import re
import sqlite3
from asyncio import Queue
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, TypedDict

from copilotkit import CopilotKitState
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, StructuredTool, tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from langgraph_swarm import SwarmState, create_swarm
from pydantic import BaseModel, Field

from dingent.core import get_app_context
from dingent.core.assistant_manager import RunnableTool
from dingent.core.log_manager import log_with_context

from .simple_react_agent import build_simple_react_agent

db_path = Path(".dingent/data/checkpoints.sqlite")
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(db_path, check_same_thread=False)


app_context = get_app_context()

llm_manager = app_context.llm_manager
assistant_manager = app_context.assistant_manager
config_manager = app_context.config_manager
workflow_manager = workflow_manager = app_context.workflow_manager
tool_call_events_queue = Queue()


# =========================
# State
# =========================


class MainState(CopilotKitState, SwarmState):
    """
    Swarm 全局状态
    """

    artifact_ids: list[str]


class SubgraphState(CopilotKitState, AgentState):
    """
    单个 assistant 子图状态
    在一次子图执行期间收集工具输出 ID；执行结束后 post_process 会消费并清空
    """

    iteration: int  # 覆盖型
    artifact_ids: list[str] = []


# =========================
# 消息/工具辅助
# =========================


def create_handoff_tool(*, agent_name: str, description: str | None = None) -> BaseTool:
    name = f"transfer_to_{agent_name}"

    @tool(name, description=description)
    async def handoff_tool(
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            goto=agent_name,
            update={"messages": [tool_message]},
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


def mcp_tool_wrapper(runnable_tool: RunnableTool) -> BaseTool:
    """
    包装 MCP 工具：采集 artifact_id 并写入当前子图状态 (SubgraphState.artifact_ids)
    """

    tool = runnable_tool.tool

    async def call_tool(
        tool_call_id: Annotated[str, InjectedToolCallId],
        **kwargs,
    ) -> Command:
        """
        适配新版 ResourceMiddleware 输出结构:
        中间件标准化后（理想/推荐做法）工具侧最终文本可能是:
          1) 仅 model_text 纯字符串           （result.content[0].text = model_text）
          2) 也可能是最小 JSON:
             {
               "artifact_id": "...",
               "model_text": "...",
               "version": "1.0"
             }

        我们这里做两件事：
          - 若能解析出 {"artifact_id","model_text"} => 使用 model_text 作为消息内容，记录 artifact_id
          - 否则把原始字符串当作对模型的消息（没有可追踪的结构化展示资源）
        """
        try:
            response_raw = await runnable_tool.run(kwargs)
            log_with_context(
                "info",
                "Tool Call Result: {response_raw}",
                context={"response_raw": response_raw, "tool_name": tool.name, "tool_call_id": tool_call_id},
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            log_with_context(
                "error",
                message="Error: {error_msg}",
                context={"error_msg": error_msg, "tool_name": tool.name, "tool_call_id": tool_call_id},
            )
            return Command(update={"messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id)]})

        structred_response: dict = response_raw.data
        artifact_id = structred_response.get("artifact_id")
        model_text = structred_response["model_text"]

        # 默认内容（若无法解析出结构化字段）
        tool_message = ToolMessage(content=model_text, tool_call_id=tool_call_id)

        return Command(
            update={
                "messages": [tool_message],
                "artifact_ids": [artifact_id] if artifact_id else [],
            },
        )

    class ToolArgsSchema(BaseModel):
        tool_call_id: Annotated[str, InjectedToolCallId]

    CombinedToolArgsSchema = create_dynamic_pydantic_class(
        ToolArgsSchema,
        tool.inputSchema,
        name=f"CombinedToolArgsSchema_{tool.name}",
    )

    return StructuredTool(
        name=tool.name,
        description=tool.description or "",
        args_schema=CombinedToolArgsSchema,
        coroutine=call_tool,
        metadata=tool.annotations.model_dump() if tool.annotations else None,
    )


def _normalize_name(name: str) -> str:
    """
    Standardizes a name to be a valid identifier.
    It replaces non-alphanumeric characters with underscores
    and ensures the name doesn't start with a digit.
    """
    # Replace any character that is not a letter, number, or underscore with an underscore
    s = re.sub(r"\W|^(?=\d)", "_", name)
    return s


@asynccontextmanager
async def create_assistant_graphs(workflow_id: str, llm):
    """
    Creates the core agent for each assistant and wraps it with post-processing.
    """
    assistant_graphs: dict[str, CompiledStateGraph] = {}
    assistants = await workflow_manager.instantiate_workflow_assistants(workflow_id, reset_assistants=False)

    # Create mappings between original and normalized names
    assistants_by_name = {a.name: a for a in assistants.values()}
    name_map = {original: _normalize_name(original) for original in assistants_by_name}

    # Create handoff tools using normalized names as identifiers
    handoff_tools: dict[str, BaseTool] = {}
    for original_name, assistant in assistants_by_name.items():
        normalized_name = name_map[original_name]
        handoff_tools[normalized_name] = create_handoff_tool(
            agent_name=normalized_name,
            # The description still uses the user-friendly original name
            description=f"Transfer the conversation to {original_name} assistant. {original_name}'s description: {assistant.description}",
        )

    async with AsyncExitStack() as stack:
        for original_name, assistant in assistants_by_name.items():
            normalized_name = name_map[original_name]

            # Load tools for the current assistant
            # tools = await stack.enter_async_context(assistant.load_tools_langgraph())
            tools: list[RunnableTool] = await stack.enter_async_context(assistant.load_tools())
            wrapped_tools = [mcp_tool_wrapper(t) for t in tools]
            # filtered_tools = [mcp_tool_wrapper(t) for t in tools if not getattr(t, "name", "").startswith("__")]

            # Get destination tools by mapping destination names to their normalized versions
            normalized_destinations = [_normalize_name(d) for d in assistant.destinations if d in name_map]
            dest_tools = [handoff_tools[norm_d] for norm_d in normalized_destinations if norm_d in handoff_tools]

            # Create the agent with the normalized name
            agent = build_simple_react_agent(
                llm=llm,
                tools=dest_tools + wrapped_tools,
                system_prompt=assistant.description,
                name=normalized_name,
            )

            # Wrap and store the compiled graph using the normalized name as the key
            assistant_graphs[normalized_name] = agent

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
            error_msg_content = f"An error occurred during this execution round: {type(e).__name__}: {e}"
            log_with_context("error", "{error_type}: {error_msg}", context={"error_type": type(e).__name__, "error_msg": error_msg_content})
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
    config = config_manager.get_settings()
    current_workflow_id = config.current_workflow
    assert current_workflow_id, "No current workflow is set in the configuration."
    current_workflow = workflow_manager.get_workflow(current_workflow_id)
    assert current_workflow, f"Workflow '{current_workflow_id}' not found."
    model_config = config.llm.model_dump()
    llm = llm_manager.get_llm(**model_config)

    start_node = next((n for n in current_workflow.nodes if n.data.isStart), None)
    if not start_node:
        raise ValueError("No start node found in the current workflow.")

    default_active_agent = _normalize_name(start_node.data.assistantName)

    async with create_assistant_graphs(current_workflow_id, llm) as assistants:
        swarm = create_swarm(
            agents=list(assistants.values()),
            state_schema=MainState,
            default_active_agent=default_active_agent,
            context_schema=ConfigSchema,
        )
        compiled_swarm = swarm.compile()

        outer = StateGraph(MainState)
        safe_swarm = get_safe_swarm(compiled_swarm)
        outer.add_node("swarm", safe_swarm)
        outer.add_edge(START, "swarm")
        outer.add_edge("swarm", END)
        async with AsyncSqliteSaver.from_conn_string(db_path.as_posix()) as checkpointer:
            compiled_graph = outer.compile(checkpointer)
            compiled_graph.name = "agent"

            yield compiled_graph
