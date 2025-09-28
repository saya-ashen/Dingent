"""
CopilotKit agent implementations and extensions.
"""

from typing import Any, cast
from copilotkit import LangGraphAgent
from copilotkit.langgraph import langchain_messages_to_copilotkit
from copilotkit.langgraph_agent import ensure_config


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
