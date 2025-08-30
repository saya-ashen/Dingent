import re
from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Annotated, Any, TypedDict

from copilotkit import CopilotKitState
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, StructuredTool, tool
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langgraph_swarm import SwarmState
from pydantic import BaseModel, Field

from dingent.core.assistant_manager import RunnableTool

from .simple_react_agent import build_simple_react_agent


class MainState(CopilotKitState, SwarmState):
    artifact_ids: list[str]


def create_handoff_tool(*, agent_name: str, description: str | None, log_method: Callable) -> BaseTool:
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
        log_method("info", "Handoff to {agent_name} via tool call {tool_call_id}", context={"agent_name": agent_name, "tool_call_id": tool_call_id})
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


def mcp_tool_wrapper(runnable_tool: RunnableTool, log_method: Callable) -> BaseTool:
    tool = runnable_tool.tool

    async def call_tool(
        tool_call_id: Annotated[str, InjectedToolCallId],
        **kwargs,
    ) -> Command:
        try:
            response_raw = await runnable_tool.run(kwargs)
            log_method(
                "info",
                "Tool Call Result: {response_raw}",
                context={"response_raw": response_raw, "tool_name": tool.name, "tool_call_id": tool_call_id},
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            log_method(
                "error",
                message="Error: {error_msg}",
                context={"error_msg": error_msg, "tool_name": tool.name, "tool_call_id": tool_call_id},
            )
            return Command(update={"messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id)]})

        structred_response: dict = response_raw.data
        artifact_id = structred_response.get("artifact_id")
        model_text = structred_response["model_text"]

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
    return re.sub(r"\W|^(?=\d)", "_", name)


@asynccontextmanager
async def create_assistant_graphs(workflow_manager, workflow_id: str, llm, log_method: Callable):
    assistant_graphs: dict[str, CompiledStateGraph] = {}
    assistants = await workflow_manager.instantiate_workflow_assistants(workflow_id, reset_assistants=False)

    assistants_by_name = {a.name: a for a in assistants.values()}
    name_map = {original: _normalize_name(original) for original in assistants_by_name}

    handoff_tools: dict[str, BaseTool] = {}
    for original_name, assistant in assistants_by_name.items():
        normalized_name = name_map[original_name]
        handoff_tools[normalized_name] = create_handoff_tool(
            agent_name=normalized_name,
            description=f"Transfer the conversation to {original_name} assistant. {original_name}'s description: {assistant.description}",
            log_method=log_method,
        )

    async with AsyncExitStack() as stack:
        for original_name, assistant in assistants_by_name.items():
            normalized_name = name_map[original_name]
            tools: list[RunnableTool] = await stack.enter_async_context(assistant.load_tools())
            wrapped_tools = [mcp_tool_wrapper(t, log_method) for t in tools]

            normalized_destinations = [_normalize_name(d) for d in assistant.destinations if d in name_map]
            dest_tools = [handoff_tools[norm_d] for norm_d in normalized_destinations if norm_d in handoff_tools]

            agent = build_simple_react_agent(
                llm=llm,
                tools=dest_tools + wrapped_tools,
                system_prompt=assistant.description,
                name=normalized_name,
            )
            assistant_graphs[normalized_name] = agent

        yield assistant_graphs


class ConfigSchema(TypedDict):
    model_provider: str
    model_name: str
    default_route: str


def get_safe_swarm(compiled_swarm: CompiledStateGraph, log_method: Callable):
    async def run_swarm_safely(state: MainState, config):
        try:
            return await compiled_swarm.ainvoke(state, config=config)
        except Exception as e:
            error_msg_content = f"An error occurred during this execution round: {type(e).__name__}: {e}"
            log_method("error", "{error_type}: {error_msg}", context={"error_type": type(e).__name__, "error_msg": error_msg_content})
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
    workflow_id: str | None = None
    from dingent.core.context import get_app_context

    gm = get_app_context().graph_manager
    graph = await gm.get_graph(workflow_id)
    yield graph
