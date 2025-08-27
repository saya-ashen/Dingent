from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from copilotkit.langgraph import copilotkit_emit_state
from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.messages.tool import ToolCall
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.state import RunnableConfig
from langgraph.types import Command


# -------- State 定义 --------
# 这里只定义 messages + iteration。其它父状态（如 facts）由父图的 TypedDict 决定。
class SimpleAgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], operator.add]
    iteration: int  # 覆盖型
    artifact_ids: list[str] = []


def build_simple_react_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str | None = None,
    max_iterations: int = 6,
    stop_when_no_tool: bool = True,
    name: str = "simple_react_agent",
):
    """
    返回一个可作为子图嵌入父图的 LangGraph 图对象（已 compile）。
    参数:
        llm: 任意兼容 .invoke(messages, tools=[...]) 的 Chat 模型
        tools: @tool 装饰的工具列表
        system_prompt: 可选系统提示
        max_iterations: 最大 LLM->Tool 循环次数
        tool_result_state_key: 如果工具返回的是非 str / dict，则把原始结果塞进这个 state key
        stop_when_no_tool: 如果模型消息没有 tool_calls，则终止

    使用方式:
        agent_app = build_simple_react_agent(...)
        # 在父图里 add_node("agent", agent_app)
    """

    name_to_tool: dict[str, BaseTool] = {t.name: t for t in tools}

    # ---- 模型节点 ----
    async def model_node(state: SimpleAgentState) -> dict[str, Any]:
        iteration = state.get("iteration", 0)
        if iteration >= max_iterations:
            # 不再继续，直接返回（不再新增 AIMessage）
            return {}

        messages: list[BaseMessage] = state.get("messages", [])

        # 如果需要把父状态中的其它字段作为“压缩上下文”注入，可在此构造：
        model_messages: list[BaseMessage] = []
        if system_prompt:
            model_messages.append(SystemMessage(content=system_prompt))

        model_messages.extend(messages)
        llm_with_tools = llm.bind_tools(tools=tools)

        response = await llm_with_tools.ainvoke(model_messages)

        # 返回 iteration+1 以及新 AI 响应
        return {
            "messages": [response],
            "iteration": iteration + 1,
        }

    async def tools_node(state: SimpleAgentState, config: RunnableConfig) -> dict[str, Any] | Command:
        # 找出最近一个包含 tool_calls 的 AIMessage
        last_ai: AIMessage | None = next(
            (m for m in reversed(state["messages"]) if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)),
            None,
        )
        if last_ai is None:
            return {}

        tool_messages: list[ToolMessage] = []
        artifact_ids: list[str] = []
        goto_data: dict[str, Any] | None = None

        for tc in last_ai.tool_calls:
            tool_name = tc.get("name")
            args = tc.get("args", {}) or {}
            tool = name_to_tool.get(tool_name)
            if tool is None:
                tool_messages.append(
                    ToolMessage(
                        content=f"[ToolError] Tool '{tool_name}' not registered.",
                        name=tool_name,
                        tool_call_id=tc.get("id"),
                    )
                )
                continue

            result: Command = await tool.ainvoke(
                ToolCall(
                    {
                        "name": tool.name,
                        "args": args,
                        "type": "tool_call",
                        "id": tc.get("id"),
                    }
                )
            )

            # 收集输出
            tool_messages.extend(result.update.get("messages", []))
            artifact_ids.extend(result.update.get("artifact_ids", []))

            # 如果存在跳转，记录（保持与原逻辑一致——后出现的覆盖先出现的）
            if result.goto:
                goto_data = {"node": result.goto, "graph": result.graph}

        updated_messages_full = state["messages"] + tool_messages
        updated_artifact_ids = state.get("artifact_ids", []) + artifact_ids

        if goto_data:
            end_command = Command(
                goto=goto_data["node"],
                graph=goto_data["graph"],
                update={
                    "messages": updated_messages_full,
                    "artifact_ids": updated_artifact_ids,
                },
            )
        else:
            # 保留原始行为：不带 goto 时 update 里只放新增的 tool_messages
            end_command = Command(
                update={
                    "messages": tool_messages,
                    "artifact_ids": updated_artifact_ids,
                }
            )

        # 向外部状态广播：总是带全量 messages（与原实现一致）
        await copilotkit_emit_state(
            config=config,
            state={
                "messages": updated_messages_full,
                "artifact_ids": updated_artifact_ids,
            },
        )
        return end_command

    # ---- 结束条件路由 ----
    async def route_after_model(state: SimpleAgentState):
        if not state.get("messages"):
            return END
        last = state["messages"][-1]
        # 如果是 AI 且有 tool_calls 并且没超过迭代限制 -> tools
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None) and state.get("iteration", 0) <= max_iterations:
            return "tools"
        # 否则终止（如果 stop_when_no_tool=True）
        if stop_when_no_tool:
            return END
        return END  # 简化：这里也直接结束

    # 构建子图
    graph = StateGraph(SimpleAgentState)
    graph.add_node("model", model_node)
    graph.add_node("tools", tools_node)

    graph.set_entry_point("model")
    graph.add_conditional_edges("model", route_after_model, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")

    compiled_graph = graph.compile()
    compiled_graph.name = name
    return compiled_graph
