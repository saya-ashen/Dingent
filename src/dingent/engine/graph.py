import json
import operator
import uuid
from asyncio import Queue
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Annotated, Any, TypedDict, cast

from copilotkit import CopilotKitState
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, StructuredTool, tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command, Send
from langgraph_swarm import SwarmState, create_swarm
from pydantic import BaseModel, Field

from dingent.core import get_assistant_manager, get_config_manager, get_llm_manager
from dingent.core.log_manager import log_with_context
from dingent.core.workflow_manager import get_workflow_manager

llm_manager = get_llm_manager()
assistant_manager = get_assistant_manager()
tool_call_events_queue = Queue()
config_manager = get_config_manager()
workflow_manager = get_workflow_manager()


# =========================
# State
# =========================
class MainState(CopilotKitState, SwarmState):
    """
    Swarm 全局状态
    （这里不再需要聚合 tool_output_ids，可留空或保留字段视需要）
    """

    pass


class SubgraphState(CopilotKitState, AgentState):
    """
    单个 assistant 子图状态
    在一次子图执行期间收集工具输出 ID；执行结束后 post_process 会消费并清空
    """

    tool_output_ids: Annotated[list, operator.concat]


# =========================
# 消息/工具辅助
# =========================
def build_action_messages(state: dict, list_of_args: list[dict]) -> list[AIMessage | ToolMessage]:
    """
    构造 show_data 工具调用消息对
    """
    actions = state.get("copilotkit", {}).get("actions", [])
    show_data_action = None
    for action in actions:
        if action.get("type") == "function" and action.get("function", {}).get("name") == "show_data":
            show_data_action = action
            break
    if show_data_action is None:
        return []

    messages: list[AIMessage | ToolMessage] = []
    for args in list_of_args:
        tool_call_id = str(uuid.uuid4())
        tool_call = ToolCall(
            name="show_data",
            args=args,
            id=tool_call_id,
        )
        messages.append(AIMessage(content="", tool_calls=[tool_call]))
        messages.append(ToolMessage(content="show data", tool_call_id=tool_call_id))
    return messages


def create_handoff_tool(*, agent_name: str, description: str | None = None) -> BaseTool:
    """
    交接工具：把对话控制权转移给指定 agent
    """
    name = f"transfer_to_{agent_name}"

    @tool(name, description=description)
    async def handoff_tool(
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
        # 去掉最后一条 AI (调用该工具的消息) 避免重复
        new_messages = cast(list, state["messages"])[:-1] + [tool_message]
        return Command(
            goto=Send(agent_name, arg={**state, "messages": new_messages}),
            update={**state, "messages": new_messages},
            graph=Command.PARENT,
        )

    return handoff_tool


json_type_to_python_type = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": float,
    "array": list,
    "object": dict,
    "null": type(None),
    "any": Any,
}


def create_dynamic_pydantic_class(
    base_class: type[BaseModel],
    schema_dict: dict,
    name: str,
) -> type[BaseModel]:
    attributes: dict[str, Any] = {}
    attributes["__annotations__"] = {}
    attributes["__annotations__"].update(getattr(base_class, "__annotations__", {}))

    attributes["model_config"] = {}
    if schema_dict.get("additionalProperties", True) is False:
        attributes["model_config"]["extra"] = "forbid"

    properties = schema_dict.get("properties", {})
    required_fields = set(schema_dict.get("required", []))

    for field_name, field_info in properties.items():
        json_type = field_info.get("type", "any")
        python_type = json_type_to_python_type.get(json_type, Any)
        is_required = field_name in required_fields
        if is_required:
            attributes["__annotations__"][field_name] = python_type
            default_value = ...
        else:
            attributes["__annotations__"][field_name] = python_type | None
            default_value = None

        attributes[field_name] = Field(
            title=field_info.get("title"),
            description=field_info.get("description"),
            default=default_value,
        )

    return type(name, (base_class,), attributes)


def mcp_tool_wrapper(_tool: StructuredTool) -> BaseTool:
    """
    包装 MCP 工具：采集 tool_output_id 并写入当前子图状态 (SubgraphState.tool_output_ids)
    """

    class ToolArgsSchema(BaseModel):
        state: Annotated[dict, InjectedState]
        tool_call_id: Annotated[str, InjectedToolCallId]

    if isinstance(_tool.args_schema, dict):
        tool_args_schema = _tool.args_schema
    else:
        tool_args_schema = _tool.args_schema.model_json_schema()

    CombinedToolArgsSchema = create_dynamic_pydantic_class(
        ToolArgsSchema,
        tool_args_schema,
        name=f"CombinedToolArgsSchema_{_tool.name}",
    )

    @tool(
        _tool.name,
        description=_tool.description,
        args_schema=CombinedToolArgsSchema,
    )
    async def call_tool(
        state: Annotated[SubgraphState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
        **kwargs,
    ) -> Command:
        try:
            response_raw = await _tool.ainvoke(kwargs)
            log_with_context(
                "info",
                "Tool Call Result: {response_raw}",
                context={"response_raw": response_raw, "tool_name": _tool.name, "tool_call_id": tool_call_id},
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            log_with_context(
                "error",
                message="Error: {error_msg}",
                context={"error_msg": error_msg, "tool_name": _tool.name, "tool_call_id": tool_call_id},
            )
            return Command(update={"messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id)]})

        messages: list = []
        collected_ids: list[str] = []

        try:
            data = json.loads(response_raw)
            if isinstance(data, dict) and {"context", "tool_output_id"} <= data.keys():
                context_text = data.get("context") or ""
                tool_output_id = data.get("tool_output_id")
                if tool_output_id:
                    collected_ids.append(tool_output_id)
                messages.append(ToolMessage(content=context_text, tool_call_id=tool_call_id))
            else:
                messages.append(ToolMessage(content=response_raw, tool_call_id=tool_call_id))
        except json.JSONDecodeError:
            messages.append(ToolMessage(content=response_raw, tool_call_id=tool_call_id))

        # 合并去重
        new_ids = list(dict.fromkeys(state.get("tool_output_ids", []) + collected_ids))
        return Command(
            update={
                "messages": messages,
                "tool_output_ids": new_ids,
            }
        )

    return call_tool


# =========================
# 包装 create_react_agent （核心：后处理添加 show_data 并清空）
# =========================
def wrap_agent_with_post_process(name: str, agent_graph: CompiledStateGraph) -> CompiledStateGraph:
    """
    WRAPPER: 把原始 create_react_agent 的 compiled 图包在一个新的 StateGraph 中
    执行顺序:
      START -> core(调用原 agent 图) -> post_process(追加 show_data & 清空 tool_output_ids) -> END
    """
    wrapper = StateGraph(SubgraphState)

    async def core_node(state: SubgraphState):
        # 直接调用原图
        return await agent_graph.ainvoke(state)

    def post_process(state: SubgraphState):
        tool_output_ids = state.get("tool_output_ids", [])
        if tool_output_ids:
            msgs = state["messages"]
            action_args = [{"tool_output_id": tid} for tid in tool_output_ids]
            action_messages = build_action_messages(state, action_args)
            if action_messages:
                msgs.extend(action_messages)
            # 清空 tool_output_ids
            return {
                **state,
                "messages": msgs,
                "tool_output_ids": [],
            }
        return state

    wrapper.add_node("core", core_node)
    wrapper.add_node("post_process", post_process)
    wrapper.add_edge(START, "core")
    wrapper.add_edge("core", "post_process")
    wrapper.add_edge("post_process", END)

    compiled = wrapper.compile()
    compiled.name = name
    return compiled


@asynccontextmanager
async def create_assistant_graphs(workflow_id: str, llm):
    """
    为每个 assistant 创建其核心 agent，然后用 wrap_agent_with_post_process 包一层
    """
    assistant_graphs: dict[str, CompiledStateGraph] = {}
    assistants = await workflow_manager.instantiate_workflow_assistants(workflow_id, reset_assistants=False)

    handoff_tools: dict[str, BaseTool] = {}
    # FIXME: assistant name 需要标准化，避免特殊字符和空格
    for assistant in assistants.values():
        handoff_tools[assistant.name] = create_handoff_tool(
            agent_name=assistant.name,
            description=f"Transfer the conversation to {assistant.name} assistant. {assistant.name} assistant's description: {assistant.description}",
        )

    async with AsyncExitStack() as stack:
        for assistant in assistants.values():
            tools = await stack.enter_async_context(assistant.load_tools_langgraph())
            filtered = [mcp_tool_wrapper(t) for t in tools if not getattr(t, "name", "").startswith("__")]
            dest_tools = [handoff_tools[d] for d in assistant.destinations if d in handoff_tools]

            base_agent = create_react_agent(
                model=llm,
                tools=dest_tools + filtered,
                state_schema=SubgraphState,
                prompt=assistant.description,
                name=assistant.name,
            )
            wrapped_agent = wrap_agent_with_post_process(assistant.name, base_agent)
            assistant_graphs[assistant.name] = wrapped_agent

        yield assistant_graphs


class ConfigSchema(TypedDict):
    model_provider: str
    model_name: str
    default_route: str


def get_safe_swarm(compiled_swarm: CompiledStateGraph):
    """
    仅负责安全执行 swarm（交给子图自己做 show_data 追加）
    """

    async def run_swarm_safely(state: MainState, config=None):
        try:
            return await compiled_swarm.ainvoke(state, config=config)
        except Exception as e:
            error_msg_content = f"抱歉，本轮执行出错：{type(e).__name__}: {e}"
            log_with_context("error", error_msg_content, context={"error_type": type(e).__name__})
            # 取最近快照
            try:
                snap = await compiled_swarm.aget_state(config)
                base_state = (getattr(snap, "values", None) or snap) if snap else state
            except Exception:
                base_state = state
            msgs = list(base_state.get("messages", [])) + [
                AIMessage(
                    content=error_msg_content,
                    additional_kwargs={"error": True, "error_type": type(e).__name__},
                )
            ]
            return {**base_state, "messages": msgs}

    return run_swarm_safely


@asynccontextmanager
async def make_graph():
    """
    构建最外层图：现在 show_data 的处理已在每个子 agent 包装内完成
    """
    config = config_manager.get_config()
    current_workflow = config_manager.get_current_workflow()
    model_config = config.llm.model_dump()
    llm = llm_manager.get_llm(**model_config)

    start_node = next((n for n in current_workflow.nodes if n.data.isStart), None)
    if not start_node:
        raise ValueError("No start node found in the current workflow.")

    async with create_assistant_graphs(current_workflow.id, llm) as assistants:
        swarm = create_swarm(
            agents=list(assistants.values()),
            state_schema=MainState,
            default_active_agent=start_node.data.assistantName,
            context_schema=ConfigSchema,
        )
        compiled_swarm = swarm.compile()

        outer = StateGraph(MainState)
        safe_swarm = get_safe_swarm(compiled_swarm)
        outer.add_node("swarm", safe_swarm)
        outer.add_edge(START, "swarm")
        outer.add_edge("swarm", END)
        compiled_graph = outer.compile()
        compiled_graph.name = "Agent"

        yield compiled_graph
