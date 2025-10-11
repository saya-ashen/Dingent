from __future__ import annotations

import asyncio
import inspect
from typing import Any, Awaitable, Callable, Iterable, List, Optional, Sequence, Tuple, Union

from copilotkit.action import Action, ActionDict, ActionResultDict
from copilotkit.agent import Agent
from copilotkit.sdk import COPILOTKIT_SDK_VERSION, AgentDict, CopilotKitContext, CopilotKitRemoteEndpoint, InfoDict
from copilotkit.exc import ActionExecutionException, ActionNotFoundException, AgentExecutionException, AgentNotFoundException
from copilotkit.types import Message, MetaEvent
from fastapi import HTTPException
from sqlalchemy import Engine
from sqlmodel import Session
from dingent.core.db.crud.workflow import list_workflows_by_user


import inspect
from typing import Any, Awaitable, Callable, List, Optional, Union

from dingent.server.auth.security import get_current_user_from_token


AgentsFactory = Callable[[CopilotKitContext], Awaitable[List[Agent]]]


import inspect
from typing import Any, Awaitable, Callable, List, Optional, Union


AgentFactory = Callable[[CopilotKitContext, str], Union[Agent, None, Awaitable[Union[Agent, None]]]]


class AsyncCopilotKitRemoteEndpoint(CopilotKitRemoteEndpoint):
    """
    仅重写会调用到 agents 的方法；actions 弃用。
    agents 不再是列表，而是一个按 name 延迟获取的工厂函数：
        async/sync factory: (context, name) -> Agent | None
    - 覆盖: info / execute_agent / get_agent_state
    - 其余保持父类逻辑不变（但 actions 恒为空）
    """

    def __init__(self, *, agent_factory: AgentFactory, engine: Engine):
        # 不将 agents/actions 交给父类，避免其初始化检查；actions 置空
        super().__init__(actions=[], agents=[])
        if not callable(agent_factory):
            raise TypeError("agent_factory must be a callable (context, name) -> Agent | None")
        self._agent_factory: AgentFactory = agent_factory
        self.engine = engine

    async def _resolve_agent(self, context: CopilotKitContext, name: str) -> Agent:
        res = self._agent_factory(context, name)
        if inspect.isawaitable(res):
            res = await res  # type: ignore[assignment]
        if res is None:
            raise AgentNotFoundException(name)
        return res  # type: ignore[return-value]

    # -------- 仅修改到 agents 的方法 --------

    async def info(self, *, context: CopilotKitContext):
        token = context.get("properties", {}).get("authorization") or context.get("headers", {}).get("authorization")
        if token and token.startswith("Bearer "):
            token = token[len("Bearer ") :].strip()
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        agents_list: List[AgentDict] = []
        with Session(self.engine) as session:
            user = get_current_user_from_token(session, token)
            workflows = list_workflows_by_user(session, user.id)
            for wf in workflows:
                agents_list.append(
                    {
                        "name": wf.name,
                        "description": wf.description or "",
                        "type": "langgraph",
                    }
                )
        actions_list: List[dict] = []

        self._log_request_info(
            title="Handling info request (name-based agent factory):",
            data=[("Context", context), ("Actions", actions_list), ("Agents", agents_list)],
        )
        return {"actions": actions_list, "agents": agents_list, "sdkVersion": COPILOTKIT_SDK_VERSION}

    async def execute_agent(  # pylint: disable=too-many-arguments
        self,
        *,
        context: CopilotKitContext,
        name: str,
        thread_id: str,
        state: dict,
        config: Optional[dict] = None,
        messages: List[Message],
        actions: List[ActionDict],
        node_name: str,
        meta_events: Optional[List[MetaEvent]] = None,
    ) -> Any:
        agent = await self._resolve_agent(context, name)

        self._log_request_info(
            title="Handling execute agent request (name-based agent factory):",
            data=[
                ("Context", context),
                ("Agent", agent.dict_repr()),
                ("Thread ID", thread_id),
                ("Node Name", node_name),
                ("State", state),
                ("Config", config),
                ("Messages", messages),
                ("Actions", actions),
                ("MetaEvents", meta_events),
            ],
        )

        try:
            result = agent.execute(
                thread_id=thread_id,
                node_name=node_name,
                state=state,
                config=config,
                messages=messages,
                actions=actions,
                meta_events=meta_events,
            )
            if inspect.isawaitable(result):
                return await result
            return result
        except Exception as error:
            raise AgentExecutionException(name, error) from error

    async def get_agent_state(
        self,
        *,
        context: CopilotKitContext,
        thread_id: str,
        name: str,
    ):
        agent = await self._resolve_agent(context, name)

        self._log_request_info(
            title="Handling get agent state request (name-based agent factory):",
            data=[("Context", context), ("Agent", agent.dict_repr()), ("Thread ID", thread_id)],
        )

        state = agent.get_state(thread_id=thread_id)
        if inspect.isawaitable(state):
            return await state
        return state
