from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from copilotkit.action import ActionDict
from copilotkit.agent import Agent
from copilotkit.exc import AgentExecutionException, AgentNotFoundException
from copilotkit.sdk import (
    COPILOTKIT_SDK_VERSION,
    AgentDict,
    CopilotKitContext,
    CopilotKitRemoteEndpoint,
)
from copilotkit.types import Message, MetaEvent
from fastapi import HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from dingent.core.db.crud.workflow import get_workflow_by_name, list_workflows_by_workspace
from dingent.core.db.crud.workspace import get_specific_user_workspace
from dingent.core.db.models import User, Workflow
from dingent.server.auth.security import get_current_user_from_token

# ---------- Types ----------


@runtime_checkable
class AgentFactory(Protocol):
    def __call__(self, workflow: Workflow, user: User, session: Session) -> Agent | None | Awaitable[Agent | None]: ...


# ---------- Utilities ----------


def _extract_bearer_token(context: CopilotKitContext) -> str | None:
    # Prefer properties.authorization, fallback to headers.authorization
    token = context.get("properties", {}).get("authorization") or context.get("headers", {}).get("authorization")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[len("Bearer ") :].strip()
    return token or None


async def _maybe_await[T](value: T | Awaitable[T]) -> T:
    return await value if inspect.isawaitable(value) else value  # type: ignore[return-value]


def _truncate(obj: Any, limit: int = 2048) -> Any:
    """Prevent runaway logs by truncating large strings/lists/dicts."""
    if isinstance(obj, str):
        return obj if len(obj) <= limit else (obj[:limit] + f"... <truncated {len(obj) - limit} chars>")
    if isinstance(obj, list):
        if len(obj) > 50:
            head = obj[:25]
            tail = obj[-5:]
            return head + [f"... <{len(obj) - 30} items omitted>"] + tail
        return obj
    if isinstance(obj, dict):
        # Shallow truncate string values only; deep truncation unnecessary in most requests
        out = {}
        for k, v in obj.items():
            out[k] = _truncate(v, limit=limit // 2) if isinstance(v, str | list | dict) else v
        return out
    return obj


@dataclass(frozen=True)
class _AgentCacheKey:
    # Consider scoping by user if your factory depends on auth/tenant-specific state.
    name: str
    # user_id: Optional[str] = None  # enable when your factory varies by user


# ---------- Endpoint ----------


class AsyncCopilotKitRemoteEndpoint(CopilotKitRemoteEndpoint):
    """
    Remote endpoint that resolves agents by name via a (possibly async) factory.

    - Keeps actions empty (deprecated in your flow)
    - Exposes: info / execute_agent / get_agent_state
    - Adds small in-memory cache for resolved Agent instances (optional)
    """

    __slots__ = ("_agent_factory", "engine", "_sessionmaker", "_cache", "_cache_lock", "_enable_cache")

    def __init__(self, *, agent_factory: AgentFactory, engine: Engine, enable_cache: bool = True):
        # Avoid parent-side validation by passing empty collections
        super().__init__(actions=[], agents=[])
        if not callable(agent_factory):
            raise TypeError("agent_factory must be a callable (context, name) -> Agent | None")
        self._agent_factory: AgentFactory = agent_factory
        self.engine = engine
        self._sessionmaker = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
        self._enable_cache = enable_cache
        self._cache: dict[_AgentCacheKey, Agent] = {}
        self._cache_lock = asyncio.Lock()

    # ---------- Private helpers ----------

    async def _resolve_agent(self, workflow: Workflow, user: User, session: Session) -> Agent:
        name = workflow.name
        key = _AgentCacheKey(name=name)

        if self._enable_cache:
            async with self._cache_lock:
                cached = self._cache.get(key)
                if cached is not None:
                    return cached

        res = self._agent_factory(workflow, user, session)
        agent = await _maybe_await(res)
        if agent is None:
            raise AgentNotFoundException(name)

        if self._enable_cache:
            async with self._cache_lock:
                self._cache[key] = agent
        return agent

    def _with_session(self) -> Session:
        # Use sessionmaker to be explicit about lifecycle; avoids implicit engine coupling
        return self._sessionmaker()

    # ---------- Overridden methods that touch agents ----------

    async def info(self, *, context: CopilotKitContext):
        token = _extract_bearer_token(context)
        workspace_slug = context.get("properties", {}).get("workspace_slug")
        if not token or not workspace_slug:
            raise HTTPException(status_code=401, detail="Missing token or workspace")

        agents_list: list[AgentDict] = []
        with self._with_session() as session:
            user = get_current_user_from_token(session, token)
            workspace = get_specific_user_workspace(session, user.id, workspace_slug)
            assert workspace is not None, "User must have access to the specified workspace"
            # If token invalid, the above should raise. Keep the HTTPException behavior in that helper.
            workflows = list_workflows_by_workspace(session, workspace.id)
            for wf in workflows:
                agents_list.append(
                    {
                        "name": wf.name,
                        "description": wf.description or "",
                        "type": "langgraph",
                    }
                )

        actions_list: list[dict] = []  # kept for schema parity

        self._log_request_info(
            title="Handling info request (factory-based agents)",
            data=[
                ("Context(meta)", {"has_properties": bool(context.get("properties")), "has_headers": bool(context.get("headers"))}),
                ("Agents(count)", len(agents_list)),
            ],
        )
        return {"actions": actions_list, "agents": agents_list, "sdkVersion": COPILOTKIT_SDK_VERSION}

    async def execute_agent(  # pylint: disable=too-many-arguments
        self,
        *,
        context: CopilotKitContext,
        name: str,
        thread_id: str,
        state: dict,
        config: dict | None = None,
        messages: list[Message],
        actions: list[ActionDict],
        node_name: str,
        meta_events: list[MetaEvent] | None = None,
    ) -> Any:
        token = _extract_bearer_token(context)
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        with self._with_session() as session:
            user = get_current_user_from_token(session, token)
            workflow = get_workflow_by_name(session, name, user.id)
            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
            agent = await self._resolve_agent(workflow, user, session)

            # Keep logs readable and safe
            self._log_request_info(
                title="Handling execute agent request (factory-based agents)",
                data=[
                    ("Agent", agent.dict_repr()),
                    ("Thread ID", thread_id),
                    ("Node Name", node_name),
                    ("State", _truncate(state)),
                    ("Config", _truncate(config or {})),
                    ("Messages(count)", len(messages)),
                    ("Actions(count)", len(actions)),
                    ("MetaEvents(count)", len(meta_events or [])),
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
                return await _maybe_await(result)
            except Exception as error:
                # Preserve original error as cause; CopilotKit aggregations expect AgentExecutionException
                raise AgentExecutionException(name, error) from error

    async def get_agent_state(
        self,
        *,
        context: CopilotKitContext,
        thread_id: str,
        name: str,
    ):
        token = _extract_bearer_token(context)
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        with self._with_session() as session:
            user = get_current_user_from_token(session, token)
            workflow = get_workflow_by_name(session, name, user.id)
            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
            agent = await self._resolve_agent(workflow, user, session)

            self._log_request_info(
                title="Handling get agent state request (factory-based agents)",
                data=[
                    ("Agent", agent.dict_repr()),
                    ("Thread ID", thread_id),
                ],
            )

            state = agent.get_state(thread_id=thread_id)
            return await _maybe_await(state)
