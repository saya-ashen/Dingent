"""
CopilotKit agent implementations and extensions.
"""

import json
from typing import Any, AsyncGenerator, cast
import uuid

from ag_ui.core import CustomEvent, StateSnapshotEvent, EventType, MessagesSnapshotEvent, RawEvent, RunAgentInput, RunErrorEvent, RunFinishedEvent, RunStartedEvent
from ag_ui_langgraph import LangGraphEventTypes
from ag_ui_langgraph.agent import langchain_messages_to_agui, dump_json_safe
from copilotkit import LangGraphAgent
from copilotkit.langgraph import langchain_messages_to_copilotkit
from copilotkit.langgraph_agent import ensure_config
from copilotkit import LangGraphAGUIAgent


class DingRunAgentInput(RunAgentInput):
    owner_id: uuid.UUID


class MockMessage:
    def __init__(self, role: str, content: str, id: str = None):
        self.role = role
        self.content = content
        self.id = id or str(uuid.uuid4())


class DingLangGraphAGUIAgent(LangGraphAGUIAgent):
    """
    自定义 Agent 类，增加了用户归属权(owner_id)标记和历史记录查询功能。
    """

    async def get_thread_messages(self, thread_id: str):
        """
        [新增功能] 根据 thread_id 获取该对话的所有历史消息。
        返回格式已转换为前端友好的 AG-UI 格式。
        """

        config = self.graph.config or {}
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["thread_id"] = thread_id

        state = await self.graph.aget_state(config)

        # 提取 messages
        messages = state.values.get("messages", [])

        yield self._dispatch_event(RunStartedEvent(type=EventType.RUN_STARTED, thread_id=thread_id, run_id="abcdefadfasdf"))
        yield self._dispatch_event(
            MessagesSnapshotEvent(type=EventType.MESSAGES_SNAPSHOT, messages=langchain_messages_to_agui(messages)),
        )


class FixedLangGraphAgent(LangGraphAgent):
    """
    Extended LangGraphAgent with fixes for thread state management.
    This is a HACK to work around issues in the base LangGraphAgent class.
    """

    async def get_state(
        self,
        *,
        thread_id: str,
    ):
        """
        Get the state of a thread, with proper handling of empty/non-existent threads.
        """
        if not thread_id:
            return {"threadId": "", "threadExists": False, "state": {}, "messages": []}

        config = ensure_config(cast(Any, self.langgraph_config.copy()) if self.langgraph_config else {})
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["thread_id"] = thread_id

        if not self.thread_state.get(thread_id, None):
            self.thread_state[thread_id] = {**(await self.graph.aget_state(config)).values}

        state = self.thread_state[thread_id]
        if state == {}:
            return {"threadId": thread_id or "", "threadExists": False, "state": {}, "messages": []}

        messages = langchain_messages_to_copilotkit(state.get("messages", []))
        state_copy = state.copy()
        state_copy.pop("messages", None)

        return {"threadId": thread_id, "threadExists": True, "state": state_copy, "messages": messages}
