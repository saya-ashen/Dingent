from typing import Any, Callable

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage, BaseMessage
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

    async def model_node(state: SimpleAgentState) -> dict[str, Any]:
        iteration = state.get("iteration", 0)
        # 简单的循环保护
        if iteration >= max_iterations:
            return {"messages": [AIMessage(content="Max iterations reached.")]}

        messages = state.get("messages", [])
        # 构造上下文：System Prompt + 历史消息
        input_messages = [SystemMessage(content=system_prompt)] + messages if system_prompt else messages

        response = await llm.bind_tools(tools).ainvoke(input_messages)

        return {
            "messages": [response],
            "iteration": iteration + 1,
        }

    async def tools_node(state: SimpleAgentState, config: RunnableConfig) -> Command:
        last_msg = state["messages"][-1]
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return Command(update={})

        # 获取插件配置
        plugin_configs = config.get("configurable", {}).get("assistant_plugin_configs", {}).get(name, {})

        new_messages: list[BaseMessage] = []
        new_artifact_ids: list[str] = []
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
            args["tool_call_id"] = tc["id"]
            if tool.tags and (plugin_name := tool.tags[0]):
                if cfg := plugin_configs.get(plugin_name):
                    args["plugin_config"] = cfg

            try:
                # 执行工具 (兼容返回 Command 或 普通结果)
                result = await tool.ainvoke(args)

                if isinstance(result, Command):
                    # 处理 Command 类型返回 (来自 handoff 或 mcp wrapper)
                    if result.update:
                        new_messages.extend(result.update.get("messages", []))
                        new_artifact_ids.extend(result.update.get("artifact_ids", []))
                    if result.goto:
                        active_goto = result  # 后续覆盖前者
                else:
                    # 处理普通工具返回 (兼容性兜底)
                    content = str(result)
                    new_messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))

            except Exception as e:
                new_messages.append(ToolMessage(content=f"Execution Error: {str(e)}", tool_call_id=tc["id"], is_error=True))

        # --- CopilotKit 状态同步 ---
        # 必须发送全量状态给前端/CopilotKit
        full_messages = state["messages"] + new_messages
        full_artifacts = state.get("artifact_ids", []) + new_artifact_ids

        await copilotkit_emit_state(
            config=config,
            state={
                "messages": full_messages,
                "artifact_ids": full_artifacts,
            },
        )

        # --- LangGraph 状态更新 ---
        # !重要修复: 这里只返回增量 (new_messages)，因为 State 定义使用了 operator.add
        return Command(
            goto=active_goto.goto if active_goto else None, graph=active_goto.graph if active_goto else None, update={"messages": new_messages, "artifact_ids": new_artifact_ids}
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
