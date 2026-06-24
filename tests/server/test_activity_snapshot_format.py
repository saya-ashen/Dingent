from __future__ import annotations

import json
import uuid

import pytest
from langchain_core.language_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph_swarm import create_swarm

from dingent.engine.agents.simple_agent import build_simple_react_agent, mcp_artifact_to_agui_display
from dingent.engine.agents.state import MainState
from dingent.server.copilot.agents import DingLangGraphAGUIAgent


class FakeLLM(FakeMessagesListChatModel):
    """Fake LLM that supports bind_tools (required by build_simple_react_agent)."""

    def bind_tools(self, tools, **kwargs):
        return self


def _structured_table_tool(rows: list[list[str]] | None = None) -> ToolMessage:
    """Return structured table data."""
    return ToolMessage(
        content="table ready",
        tool_call_id="call_table_test",
        artifact={
            "structured_content": {
                "model_text": "Here is the table",
                "display": [
                    {
                        "type": "table",
                        "title": "Users",
                        "columns": ["name", "age"],
                        "rows": [["Alice", "30"], ["Bob", "25"]],
                    }
                ],
            }
        },
    )


def _build_run_input(messages, thread_id=None, run_id=None):
    from ag_ui.core import RunAgentInput

    return RunAgentInput(
        thread_id=thread_id or str(uuid.uuid4()),
        run_id=run_id or str(uuid.uuid4()),
        parent_run_id=None,
        state={},
        messages=messages,
        tools=[],
        context=[],
        forwarded_props={},
    )


def _event_dict(event) -> dict:
    """Normalize an event to a plain dict for assertions."""
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        return event.model_dump()
    if hasattr(event, "__dict__"):
        return {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
    return {"raw": str(event)}


@pytest.mark.asyncio
async def test_activity_snapshot_events_contain_correct_fields():
    """Verify ACTIVITY_SNAPSHOT events have correct field names (snake_case) and content shape."""
    llm = FakeLLM(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "_structured_table_tool", "args": {"rows": [["Alice", "30"]]}, "id": "call_table_test"}],
            ),
            AIMessage(content="Done"),
        ]
    )
    agent_graph = build_simple_react_agent("agent", llm, tools=[_structured_table_tool], system_prompt="You are Agent")
    graph = create_swarm(agents=[agent_graph], state_schema=MainState, default_active_agent="agent", context_schema=dict).compile(checkpointer=InMemorySaver())
    agent = DingLangGraphAGUIAgent(name="test", graph=graph)

    input_data = _build_run_input(messages=[{"id": "m1", "role": "user", "content": "show table"}])

    snapshot_events = []
    async for raw_event in agent.run(input_data):
        event = _event_dict(raw_event) if not isinstance(raw_event, dict) else raw_event
        event_type = event.get("type")
        if event_type is not None:
            event_type = str(event_type)
        if event_type and "ACTIVITY_SNAPSHOT" in event_type:
            snapshot_events.append(event)

    assert len(snapshot_events) >= 1, "No ACTIVITY_SNAPSHOT events found. The tool artifact may not be flowing through the snapshot path."

    for snap in snapshot_events:
        assert "message_id" in snap or "messageId" in snap, f"Snapshot missing message id: keys={list(snap.keys())}"
        assert "activity_type" in snap or "activityType" in snap, f"Snapshot missing activity_type: keys={list(snap.keys())}"

        activity_type = snap.get("activity_type") or snap.get("activityType") or ""
        assert "a2ui-surface" in str(activity_type), f"Unexpected activity_type: {activity_type}"

        content = snap.get("content")
        assert content is not None, "Snapshot missing content"
        assert isinstance(content, dict), f"Content should be a dict, got {type(content).__name__}"

        if "a2ui_operations" in content:
            assert isinstance(content["a2ui_operations"], list), "a2ui_operations should be a list"
            assert len(content["a2ui_operations"]) > 0, "a2ui_operations should not be empty"
            assert content.get("surfaceId") is not None, "a2ui_operations content should have surfaceId"
        elif content.get("type") in ("table", "markdown"):
            assert "title" in content, f"Legacy {content['type']} content should have title"
        else:
            pytest.fail(f"Unexpected content shape: {json.dumps(content, indent=2)[:500]}")


@pytest.mark.asyncio
async def test_plain_text_tool_produces_no_snapshot():
    """A tool without artifact/display should NOT produce ACTIVITY_SNAPSHOT events."""
    llm = FakeLLM(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "_plain_text_tool", "args": {}, "id": "call_plain"}]),
            AIMessage(content="Done"),
        ]
    )

    @tool
    def _plain_text_tool() -> ToolMessage:
        """Return plain text result (no artifact.display)."""
        return ToolMessage(content="plain result text", tool_call_id="call_plain")

    agent_graph = build_simple_react_agent("agent", llm, tools=[_plain_text_tool], system_prompt="You are Agent")
    graph = create_swarm(agents=[agent_graph], state_schema=MainState, default_active_agent="agent", context_schema=dict).compile(checkpointer=InMemorySaver())
    agent = DingLangGraphAGUIAgent(name="test", graph=graph)

    input_data = _build_run_input(messages=[{"id": "m1", "role": "user", "content": "plain text"}])

    snapshot_events = []
    async for raw_event in agent.run(input_data):
        event = _event_dict(raw_event) if not isinstance(raw_event, dict) else raw_event
        event_type = event.get("type")
        if event_type is not None:
            event_type = str(event_type)
        if event_type and "ACTIVITY_SNAPSHOT" in event_type:
            snapshot_events.append(event)

    assert len(snapshot_events) == 0, f"Expected no ACTIVITY_SNAPSHOT for plain text tool, got {len(snapshot_events)}"


@pytest.mark.asyncio
async def test_tool_call_events_contain_tool_call_result():
    """Verify that tool calls produce TOOL_CALL_START/END/RESULT events in the stream."""
    llm = FakeLLM(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "_structured_table_tool", "args": {"rows": [["Alice", "30"]]}, "id": "call_table_test"}],
            ),
            AIMessage(content="Done"),
        ]
    )
    agent_graph = build_simple_react_agent("agent", llm, tools=[_structured_table_tool], system_prompt="You are Agent")
    graph = create_swarm(agents=[agent_graph], state_schema=MainState, default_active_agent="agent", context_schema=dict).compile(checkpointer=InMemorySaver())
    agent = DingLangGraphAGUIAgent(name="test", graph=graph)

    input_data = _build_run_input(messages=[{"id": "m1", "role": "user", "content": "show table"}])

    tool_call_starts = []
    tool_call_results = []
    async for raw_event in agent.run(input_data):
        event = _event_dict(raw_event) if not isinstance(raw_event, dict) else raw_event
        event_type = event.get("type")
        if event_type is not None:
            event_type = str(event_type)
        if event_type and "TOOL_CALL_START" in event_type:
            tool_call_starts.append(event)
        if event_type and "TOOL_CALL_RESULT" in event_type:
            tool_call_results.append(event)

    assert len(tool_call_starts) >= 1, "Should have at least one TOOL_CALL_START"
    assert len(tool_call_results) >= 1, "Should have at least one TOOL_CALL_RESULT"


@pytest.mark.asyncio
async def test_mcp_artifact_to_agui_display_returns_correct_items():
    """Verify mcp_artifact_to_agui_display produces correct output for multi-item artifacts."""
    artifact = [
        {"type": "table", "title": "Scores", "columns": ["player", "score"], "rows": [["Alice", 95], ["Bob", 87]]},
        {"type": "markdown", "title": "Summary", "content": "**Alice** won with 95 points."},
    ]
    display = mcp_artifact_to_agui_display(
        tool_name="test_tool",
        query_args={},
        surface_base_id="call_multi_test",
        artifact=artifact,
    )

    assert isinstance(display, list)
    assert len(display) == 2

    # Display order: markdown items appended during loop iteration, A2UI surface appended after loop
    md_item = display[0]
    assert md_item.get("type") == "markdown", f"First item expected markdown, got: {md_item.get('type')}"
    assert "Alice" in md_item.get("content", "")

    a2ui_item = display[1]
    assert isinstance(a2ui_item, dict)
    assert "a2ui_operations" in a2ui_item, "Second item should be a2ui_operations for the table"
    assert a2ui_item.get("surfaceId") is not None
    assert len(a2ui_item["a2ui_operations"]) > 0


@pytest.mark.asyncio
async def test_ding_langchain_messages_to_agui_handles_multi_item_content():
    """Verify that ding_langchain_messages_to_agui converts multi-item activity messages correctly."""
    from dingent.engine.agents.messages import ActivityMessage as DingActivityMessage
    from dingent.server.copilot.agents import ding_langchain_messages_to_agui

    # Create a dingent ActivityMessage with 2 content items (simulating multi-item display)
    multi_content = [
        {"type": "markdown", "title": "Summary", "content": "First item"},
        {"a2ui_operations": [{"op": "create"}], "surfaceId": "surf-0"},
    ]
    ding_msg = DingActivityMessage(id="call_test:activity", content=multi_content)

    langchain_messages = [ding_msg]
    agui_messages = ding_langchain_messages_to_agui(langchain_messages)

    # Should produce 2 ActivityMessage objects (one per content item)
    activity_msgs = [m for m in agui_messages if getattr(m, "role", None) == "activity"]
    assert len(activity_msgs) == 2, f"Expected 2 activity messages for 2 content items, got {len(activity_msgs)}"

    # First should be the markdown item
    assert activity_msgs[0].content.get("type") == "markdown"
    assert activity_msgs[0].content.get("content") == "First item"
    assert activity_msgs[0].id == "call_test:activity:0"

    # Second should be the a2ui item
    assert "a2ui_operations" in activity_msgs[1].content
    assert activity_msgs[1].id == "call_test:activity:1"

    # Single-item content should still work unchanged
    single_content = [{"type": "markdown", "content": "Single item"}]
    ding_msg_single = DingActivityMessage(id="call_test_single:activity", content=single_content)
    agui_messages_single = ding_langchain_messages_to_agui([ding_msg_single])
    activity_msgs_single = [m for m in agui_messages_single if getattr(m, "role", None) == "activity"]
    assert len(activity_msgs_single) == 1
    assert activity_msgs_single[0].id == "call_test_single:activity"  # No index suffix for single item
