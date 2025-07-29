import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_community.chat_models.fake import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import StructuredTool, tool

from dingent.engine.backend.core.graph import create_assistants, make_graph
from dingent.engine.backend.core.settings import AppSettings, MCPServerInfo
from dingent.engine.shared.llm_manager import LLMManager


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


class FakeChatModelWithBindTools(FakeMessagesListChatModel):
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


class TestAgentGraph:
    """
    A unified test suite for the LangGraph Agent Swarm using pytest.
    It combines unit tests for specific functions like `create_assistants`
    and integration tests for the full agent flow.
    """

    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        """
        A pytest fixture that runs automatically for every test in this class.
        It sets up mock objects and tool definitions.
        """
        self.mock_client = MagicMock()

        # Mock tool definitions for the end-to-end test
        self.mock_idog_search_tool = StructuredTool.from_function(
            name="search_in_idog", description="Searches the idog database.", func=self.mock_idog_search_func
        )
        self.mock_bioka_search_tool = StructuredTool.from_function(
            name="search_in_bioka", description="Searches the bioka database.", func=self.mock_bioka_search_func
        )

    def mock_idog_search_func(self, *args, **kwargs):
        """A mock implementation of the idog tool's invocation."""
        print("--- MOCK: idog tool called ---")
        diseases = ["Canine Hip Dysplasia", "Allergies", "Cataracts"]
        return json.dumps(
            {
                "context": f"Found the following top {len(diseases)} diseases for Shiba Inu: {', '.join(diseases)}",
                "tool_output": {"diseases": diseases},
                "source": "idog_mock_db",
            }
        )

    def mock_bioka_search_func(self, *args, **kwargs):
        """A mock implementation of the bioka tool's invocation."""
        print(f"--- MOCK: bioka tool called with args: {kwargs} ---")
        input_diseases = kwargs.get("tool_output", {}).get("data", {}).get("diseases", [])
        biomarkers = {d: [f"Marker_{d[:3]}_1", f"Marker_{d[:3]}_2"] for d in input_diseases}
        return json.dumps(
            {
                "context": f"Found biomarkers for the following diseases: {', '.join(biomarkers.keys())}",
                "tool_output": {"biomarkers": biomarkers},
                "source": "bioka_mock_db",
            }
        )

    @pytest.mark.asyncio
    @patch("dingent.engine.backend.core.graph.llm_manager")
    @patch("dingent.engine.backend.core.graph.load_mcp_tools", new_callable=AsyncMock)
    async def test_create_assistants(self, mock_load_mcp_tools, mock_llm_manager):
        """
        Tests the `create_assistants` function to ensure it correctly builds assistants
        based on server configurations. (This is your original test, adapted).
        """
        # --- Mocking ---
        mock_llm_manager.get_llm.return_value = MagicMock()
        mock_load_mcp_tools.return_value = [multiply]  # Use a simple mock tool

        mock_info_response = MagicMock()
        mock_info_response.text = json.dumps({"description": "A test server."})
        self.mock_client.read_resource = AsyncMock(return_value=[mock_info_response])

        mcp_servers: list[MCPServerInfo] = [
            MCPServerInfo(name="idog", host="127.0.0.1", port=8888, routable_nodes=["bioka"]),
            MCPServerInfo(name="bioka", host="127.0.0.1", port=8889, routable_nodes=["idog"]),
        ]

        # --- Execution ---
        assistants = await create_assistants(
            mcp_servers,
            {"bioka": self.mock_client, "idog": self.mock_client},
            "openai",
            "gpt-4.1-mini",
        )

        # --- Assertion ---
        assert len(assistants) == 2
        assert "bioka_assistant" in assistants
        assert "idog_assistant" in assistants
        # Ensure the client was called to get server info for each server
        assert self.mock_client.read_resource.call_count == 2

    @pytest.mark.asyncio
    @patch("dingent.engine.backend.core.graph.llm_manager", spec=LLMManager)
    @patch("dingent.engine.backend.core.graph.get_async_mcp_manager", autospec=True)
    @patch("dingent.engine.backend.core.graph.load_mcp_tools", new_callable=AsyncMock)
    @patch("dingent.engine.backend.core.graph.settings", spec=AppSettings)
    async def test_full_agent_flow_with_handoff(
        self, mock_settings, mock_load_mcp_tools, mock_get_mcp_manager, mock_llm_manager
    ):
        """
        Tests the complete agent flow from an initial query to a handoff and final answer.
        It simulates a user asking for data from two different agent capabilities.
        """
        # 1. --- Configure Mocks ---

        # Mock settings to define two agent nodes that can route to each other
        mock_settings.mcp_servers = [
            MCPServerInfo(name="idog", host="127.0.0.1", port=8888, routable_nodes=["bioka"]),
            MCPServerInfo(name="bioka", host="127.0.0.1", port=8889, routable_nodes=[]),
        ]
        # mock_get_settings.return_value = mock_settings

        # Mock the LLM to provide a deterministic sequence of responses
        llm_responses: list[BaseMessage] = [
            AIMessage(
                content="",
                tool_calls=[{"name": "search_in_idog", "args": {"query": "Shiba Inu diseases"}, "id": "call_1"}],
            ),
            AIMessage(content="", tool_calls=[{"name": "transfer_to_bioka_assistant", "args": {}, "id": "call_2"}]),
            AIMessage(content="", tool_calls=[{"name": "search_in_bioka", "args": {}, "id": "call_3"}]),
            AIMessage(
                content="I found that Shiba Inus are prone to Canine Hip Dysplasia, Allergies, and Cataracts. Associated biomarkers include Marker_Can_1, Marker_All_1, etc."
            ),
        ]
        mock_llm_manager.get_llm.return_value = FakeChatModelWithBindTools(responses=llm_responses)

        # Mock MCP clients and the context manager that provides them
        mock_idog_client = MagicMock(session=MagicMock())
        mock_idog_client.read_resource.return_value = [
            MagicMock(text=json.dumps({"description": "Agent for dog breeds."}))
        ]
        mock_info_response1 = MagicMock()
        mock_info_response1.text = json.dumps({"description": "An idog server."})
        mock_idog_client.read_resource = AsyncMock(return_value=[mock_info_response1])

        mock_bioka_client = MagicMock(session=MagicMock())
        mock_bioka_client.read_resource.return_value = [
            MagicMock(text=json.dumps({"description": "Agent for biomarkers."}))
        ]
        mock_info_response2 = MagicMock()
        mock_info_response2.text = json.dumps({"description": "A bioka server."})
        mock_bioka_client.read_resource = AsyncMock(return_value=[mock_info_response2])

        mock_mcp_manager_instance = MagicMock()
        mock_mcp_manager_instance.active_clients = {"idog": mock_idog_client, "bioka": mock_bioka_client}
        mock_get_mcp_manager.return_value.__aenter__.return_value = mock_mcp_manager_instance

        # Mock `load_mcp_tools` to return different tools based on the agent being built
        def load_tools_side_effect(session):
            if session == mock_idog_client.session:
                return [self.mock_idog_search_tool]
            if session == mock_bioka_client.session:
                return [self.mock_bioka_search_tool]
            return []

        mock_load_mcp_tools.side_effect = load_tools_side_effect

        # 2. --- Execute the Test ---

        input_messages = [
            {
                "role": "user",
                "content": "In idog, find top diseases for Shiba Inu, then in bioka, find their biomarkers.",
            }
        ]
        config = {"configurable": {"model_provider": "fake", "model_name": "fake", "default_agent": "idog"}}

        final_state = None
        async with make_graph(config) as graph:
            async for chunk in graph.astream({"messages": input_messages}, config=config, debug=True):
                print(f"\n--- STREAM CHUNK: {chunk} ---\n")
                final_state = chunk

        # 3. --- Assert Results ---

        assert final_state is not None, "The graph did not generate outputs."

        assert "bioka_assistant" in final_state.keys()
        assert "Canine Hip Dysplasia" in final_state["bioka_assistant"]["messages"][-1].content

        assert mock_load_mcp_tools.call_count == 2, "Expected to load tools for two different agents."
