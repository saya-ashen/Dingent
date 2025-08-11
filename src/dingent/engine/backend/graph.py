import json
import uuid
from asyncio import Queue
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Annotated, Any, TypedDict, cast

from copilotkit import CopilotKitState
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langchain_core.tools import InjectedToolCallId, StructuredTool, tool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command, Send
from langgraph_swarm import create_swarm
from langgraph_swarm.swarm import SwarmState
from pydantic import BaseModel, Field

from .assistant import get_assistant_manager
from .llm_manager import get_llm_manager
from .settings import get_settings

llm_manager = get_llm_manager()
assistant_manager = get_assistant_manager()
tool_call_events_queue = Queue()


client_resource_id_map: dict[str, str] = {}


class MainState(CopilotKitState, SwarmState):
    pass


class SubgraphState(CopilotKitState, AgentState):
    pass


def call_actions(state, list_of_args: list[dict]):
    actions = state.get("copilotkit", {}).get("actions", [])
    show_data_action = None
    for action in actions:
        if action["name"] == "show_data":
            show_data_action = action
    if show_data_action is None:
        return []
    action_call_messages = []
    for args in list_of_args:
        tool_call_id = f"{uuid.uuid4()}"
        tool_call = ToolCall(
            name="show_data",
            args=args,
            id=tool_call_id,
        )
        action_call_messages.append(AIMessage(content="", tool_calls=[tool_call]))
        action_call_messages.append(ToolMessage(content="show data", tool_call_id=tool_call_id))
    return action_call_messages


def create_handoff_tool(*, agent_name: str, description: str | None = None):
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

        return Command(
            goto=Send(agent_name, arg={**state, "messages": state["messages"][:-1]}),
            update={**state, "messages": cast(list, state["messages"]) + [tool_message]},
            graph=Command.PARENT,
        )

    return handoff_tool


json_type_to_python_type = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": float,  # Could also be int depending on context, float is safer default for number
    "array": list,
    "object": dict,
    "null": type(None),  # For nullable types
    "any": Any,
}


def create_dynamic_pydantic_class(
    base_class: type[BaseModel],
    schema_dict: dict,
    name: str,
) -> type[BaseModel]:
    """
    Dynamically create a new Pydantic class, which inherit base_class provided and add fields in schema_dict.

    Args:
        base_class: The base class that needs to be inherited
        schema_dict: A json schema dictionary which includes property definition.
        name: The name of the new class returned

    Returns:
        The dynamically created Pydantic class.
    """
    attributes = {}

    attributes["__annotations__"] = {}
    attributes["__annotations__"].update(base_class.__annotations__)

    attributes["model_config"] = {}
    if schema_dict.get("additionalProperties", True) is False:
        attributes["model_config"]["extra"] = "forbid"
    properties = schema_dict.get("properties", {})
    required_fields = set(schema_dict.get("required", []))

    for field_name, field_info in properties.items():
        json_type = field_info.get("type", "any")
        python_type = json_type_to_python_type.get(json_type, Any)

        is_required = field_name in required_fields

        if not is_required:
            attributes["__annotations__"][field_name] = python_type | None
        else:
            attributes["__annotations__"][field_name] = python_type

        default_value = ... if is_required else None

        field_definition = Field(title=field_info.get("title"), description=field_info.get("description"), default=default_value)

        attributes[field_name] = field_definition

    DynamicClass = type(name, (base_class,), attributes)

    return DynamicClass


def mcp_tool_wrapper(_tool: StructuredTool, client_name):
    """
    Add a wrapper for tool which is obtained from mcp service, to support advanced funcitons in langgraph
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
        name="CombinedToolArgsSchema",
    )

    @tool(
        _tool.name,
        description=_tool.description,
        args_schema=CombinedToolArgsSchema,
    )
    async def call_tool(
        state: Annotated[MainState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
        **kwargs,
    ) -> Command:
        response_raw = await _tool.ainvoke(kwargs)
        try:
            response = json.loads(response_raw)
            if {"context", "tool_outputs"}.issubset(response.keys()):
                context = response.get("context", response_raw)
                tool_output_id = response.get("tool_output_id")
                if tool_output_id:
                    client_resource_id_map[tool_output_id] = client_name
                messages = [ToolMessage(context, tool_call_id=tool_call_id)]
                action_data = {"tool_output_id": tool_output_id}
                messages.extend(call_actions(state, [action_data]))
            else:
                messages = [ToolMessage(response_raw, tool_call_id=tool_call_id)]
        except json.JSONDecodeError:
            response = {"context": response_raw}
        return Command(
            update={
                "messages": messages,
            }
        )

    return call_tool


@asynccontextmanager
async def create_assistant_graphs(llm):
    """
    Creates assistants by first concurrently gathering all server details
    and then concurrently building each assistant.
    """

    # TODO: Add Gabriel Assistant
    assistant_graphs: dict[str, CompiledStateGraph] = {}
    for name, assistant in assistant_manager.assistants.items():
        async with AsyncExitStack() as stack:
            tools = await stack.enter_async_context(assistant.load_tools_langgraph())
            filtered_tools = [mcp_tool_wrapper(tool, name) for tool in tools if not tool.name.startswith("__")]
            graph = create_react_agent(
                model=llm,
                tools=filtered_tools,
                state_schema=SubgraphState,
                prompt=assistant.description,
                name=f"{name}",
            )
            assistant_graphs[assistant.name] = graph
            yield assistant_graphs


class ConfigSchema(TypedDict):
    model_provider: str
    model_name: str
    default_route: str


@asynccontextmanager
async def make_graph(config):
    settings = get_settings()
    default_active_agent = config.get("configurable", {}).get("default_agent") or settings.default_assistant
    model_config = config.get("configurable", {}).get("llm_config") or config.get("configurable", {}).get("model_config")
    if not model_config:
        model_config = settings.llm
    llm = llm_manager.get_llm(**model_config)
    async with create_assistant_graphs(llm) as assistants:
        if not default_active_agent:
            print("No default active agent specified, using the first available assistant.")
            default_active_agent = list(assistants.keys())[0]
        else:
            default_active_agent = f"{default_active_agent}"

        swarm = create_swarm(
            agents=list(assistants.values()),
            state_schema=MainState,
            default_active_agent=default_active_agent,
            context_schema=ConfigSchema,
        )
        graph = swarm.compile()
        graph.name = "Agent"
        yield graph
