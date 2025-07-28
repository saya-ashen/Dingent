import json
from typing import Annotated, cast

import pytest
import pytest_asyncio
from langchain_core.tools import tool
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import END
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from mcp.types import TextResourceContents
from pydantic import BaseModel

from backend.core.graph import create_dynamic_pydantic_class, create_handoff_tool


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def tool_call_prompt_text() -> str:
    prompt = Prompt(alias="tool_call_prompt")
    prompt.pull()
    return cast(str, prompt.interpolate())


@pytest.fixture(scope="session")
def current_tool_descriptions(request) -> dict[str, str]:
    """
    Provides tool descriptions. Tests can override this by parametrizing
    this fixture indirectly.
    Example in test: @pytest.mark.parametrize("current_tool_descriptions",
                                              [{"text2sql": "desc A", "rag": "desc B"}],
                                              indirect=True)
    """
    default_descs = {
        "text2sql": "Default text2sql description if not overridden.",
        "rag": "Default rag description if not overridden.",
    }
    if hasattr(request, "param") and request.param:
        if isinstance(request.param, dict):
            default_descs.update(request.param)
            return default_descs
        else:
            return request.param
    return default_descs


@pytest_asyncio.fixture(scope="session")
async def mocked_create_handoff_agent(current_tool_descriptions: dict[str, dict[str, str]]):
    """
    used to change the tool description
    """

    async def _mock_loader(active_clients):  # Match signature of original
        for server_name, client in active_clients.items():
            tools = await load_mcp_tools(client.session)
            for tool_ in tools:
                description = current_tool_descriptions.get(server_name, {}).get(tool_.name, "")
                if description:
                    tool_.description = description
            server_info = await client.read_resource("resource://server_info")
            server_info = json.loads(cast(TextResourceContents, server_info[0]).text)
            description = server_info.get("description", "")

            name = server_name
            subgraph = create_subgraph(tools)

            handoff = create_handoff_tool(agent_name=name, description=description)
            yield handoff, name, subgraph

    return _mock_loader  # Return the function to be used as side_effect


@pytest_asyncio.fixture(scope="session")
async def mock_create_tool_call_agent():
    """
    Change tool to END
    """

    def _mock_loader(_tool):
        class ToolArgsSchema(BaseModel):
            state: Annotated[dict, InjectedState]

        tool_args_schema = cast(dict, _tool.args_schema or {})
        try:
            tool_args_schema["properties"].pop("args")  # type: ignore
        except:
            print("args not in schema")

        CombinedToolArgsSchema = create_dynamic_pydantic_class(
            ToolArgsSchema,
            tool_args_schema,
            name="CombinedToolArgsSchema",  # 你可以使用任何有效的类名
        )

        @tool(
            _tool.name,
            description=_tool.description,
            args_schema=CombinedToolArgsSchema,
        )
        async def call_tool(
            state: Annotated[dict, InjectedState],
            **kwargs,
        ):
            tool_message = {
                "role": "tool",
                "content": f"Successfully called to {_tool.name}",
                "name": _tool.name,
                "tool_call_id": 1,
            }
            return Command(
                goto=END,
                update={**state, "messages": state["messages"] + [tool_message]},
                graph=Command.PARENT,
            )

        return call_tool

    return _mock_loader
