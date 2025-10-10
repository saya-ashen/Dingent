"""
CopilotKit agent implementations and extensions.
"""

from typing import Any, Callable, cast
from copilotkit import Agent, LangGraphAgent
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


class LazyFixedLangGraphAgent(Agent):
    def __init__(self, name: str, description: str, builder: Callable[..., FixedLangGraphAgent]):
        # 仅保存 name / 描述 / 构建器；不做重初始化
        self._name = name
        self._description = description
        self._builder = builder
        self._real: FixedLangGraphAgent | None = None

    # 让筛选语句只读取到轻量字段，不触发构建
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, *args: Any, **kwargs: Any) -> None:
        return self._ensure().execute(*args, **kwargs)

    def get_state(self, *args: Any, **kwargs: Any):
        return self._ensure().get_state(*args, **kwargs)

    def _ensure(self) -> FixedLangGraphAgent:
        if self._real is None:
            self._real = self._builder()
        return self._real

    # 框架可能直接访问的属性/方法，统统懒转发
    def __getattr__(self, attr):
        # name/description 已在本对象
        if attr in {"name", "description"}:
            return getattr(self, f"_{attr}")
        return getattr(self._ensure(), attr)

    def __repr__(self) -> str:
        return f"<LazyFixedLangGraphAgent name={self._name} materialized={self._real is not None}>"
