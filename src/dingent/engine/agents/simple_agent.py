from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.tools import StructuredTool
from langchain.chat_models.base import BaseChatModel
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from langgraph.types import Command
from copilotkit.langgraph import copilotkit_emit_state

from .state import SimpleAgentState


def build_simple_react_agent(
    name: str,
    llm: BaseChatModel,
    tools: list[StructuredTool],
    system_prompt: str | None = None,
    max_iterations: int = 6,
    stop_when_no_tool: bool = True,
) -> CompiledStateGraph:
    name_to_tool = {t.name: t for t in tools}
    LLM_SAFE_TYPES = (SystemMessage, HumanMessage, AIMessage, ToolMessage)

    async def model_node(state: SimpleAgentState) -> dict[str, Any]:
        iteration = state.get("iteration", 0)
        # 简单的循环保护
        if iteration >= max_iterations:
            return {"messages": [AIMessage(content="Max iterations reached.")]}

        all_messages = state.get("messages", [])
        filtered_messages = [msg for msg in all_messages if isinstance(msg, LLM_SAFE_TYPES)]

        if system_prompt:
            input_messages = [SystemMessage(content=system_prompt)] + filtered_messages
        else:
            input_messages = filtered_messages

        response = await llm.bind_tools(tools).ainvoke(input_messages)

        return {
            "messages": [response],
            "iteration": iteration + 1,
        }

    async def tools_node(state: SimpleAgentState, config: RunnableConfig) -> Command:
        last_msg = state.get("messages", [])[-1]
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return Command(update={})

        # 获取插件配置
        plugin_configs = config.get("configurable", {}).get("assistant_plugin_configs", {})

        new_messages: list[BaseMessage] = []
        active_goto: Command | None = None

        for tc in last_msg.tool_calls:
            tool_name = tc["name"]
            tool = name_to_tool.get(tool_name)

            # 处理工具不存在的情况
            if not tool:
                new_messages.append(ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tc["id"], is_error=True))
                continue

            # 注入配置参数
            args = tc.get("args", {})
            if tool.tags and (plugin_name := tool.tags[0]):
                if cfg := plugin_configs.get(plugin_name):
                    args["plugin_config"] = cfg.get("config")

            try:
                # 执行工具 (兼容返回 Command 或 普通结果)
                result = await tool.ainvoke(
                    {
                        "id": tc["id"],
                        "name": tool_name,
                        "args": args,
                        "tool_call_id": tc["id"],
                        "type": "tool_call",
                    }
                )

                if isinstance(result, Command):
                    # 处理 Command 类型返回 (来自 handoff 或 mcp wrapper)
                    if result.update:
                        new_messages.extend(result.update.get("messages", []))
                    if result.goto:
                        active_goto = result  # 后续覆盖前者
                else:
                    # 处理普通工具返回 (兼容性兜底)
                    content = str(result)
                    new_messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))

            except Exception as e:
                new_messages.append(ToolMessage(content=f"Execution Error: {str(e)}", tool_call_id=tc["id"], is_error=True))

        return Command(
            goto=active_goto.goto if active_goto else [],
            graph=active_goto.graph if active_goto else None,
            update={
                "messages": new_messages,
            },
        )

    def route_after_model(state: SimpleAgentState):
        messages = state.get("messages", [])
        if not messages:
            return END

        last_msg = messages[-1]
        has_tool_calls = isinstance(last_msg, AIMessage) and bool(last_msg.tool_calls)

        if has_tool_calls and state.get("iteration", 0) <= max_iterations:
            return "tools"

        if stop_when_no_tool or not has_tool_calls:
            return END

        return END

    workflow = StateGraph(SimpleAgentState)
    workflow.add_node("model", model_node)
    workflow.add_node("tools", tools_node)
    workflow.set_entry_point("model")
    workflow.add_conditional_edges("model", route_after_model)
    workflow.add_edge("tools", "model")

    compiled = workflow.compile()
    compiled.name = name
    return compiled
