from __future__ import annotations
from copilotkit.agent import Agent
import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Dict, Protocol, runtime_checkable
from uuid import UUID
from copilotkit.sdk import CopilotKitRemoteEndpoint, CopilotKitContext
from copilotkit.types import Message, MetaEvent
from copilotkit.action import ActionDict
from copilotkit.exc import AgentExecutionException, AgentNotFoundException
from fastapi import HTTPException
from sqlmodel import Session
from dingent.core.db.models import User, Workflow
from dingent.core.db.crud.workflow import get_workflow_by_name, list_workflows_by_workspace
from dingent.core.db.crud.workspace import get_specific_user_workspace

# ---------- Types ----------


@runtime_checkable
class AgentFactory(Protocol):
    def __call__(self, workflow: Workflow, user: User, session: Session) -> Agent | None | Awaitable[Agent | None]: ...


@dataclass(frozen=True)
class _AgentCacheKey:
    # Consider scoping by user if your factory depends on auth/tenant-specific state.
    name: str
    # user_id: Optional[str] = None  # enable when your factory varies by user


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


class AsyncCopilotKitRemoteEndpoint(CopilotKitRemoteEndpoint):
    """
    重构后的 Endpoint，更像是一个 Service。
    它不再负责 HTTP 解析，而是专注于业务逻辑：根据 User 和 Session 执行 Agent。
    """

    def __init__(self, *, agent_factory: AgentFactory, enable_cache: bool = True):
        super().__init__(actions=[], agents=[])
        self._agent_factory = agent_factory
        self._enable_cache = enable_cache
        self._cache = {}
        self._cache_lock = asyncio.Lock()

    async def _resolve_agent(self, workflow: Workflow, user: User, session: Session) -> Any:
        name = workflow.name
        key = _AgentCacheKey(name=name)

        if self._enable_cache:
            async with self._cache_lock:
                cached = self._cache.get(key)
                if cached is not None:
                    return cached

        agent = self._agent_factory(workflow, user, session)
        if agent is None:
            raise AgentNotFoundException(name)
        if self._enable_cache:
            async with self._cache_lock:
                self._cache[key] = agent
        return agent

    async def execute_agent_with_user(
        self,
        *,
        user: User,
        session: Session,
        name: str,
        thread_id: str,
        state: Dict[str, Any],
        messages: list[Message],
        actions: list[ActionDict],
        node_name: str | None = None,
        config: Dict[str, Any] | None = None,
        meta_events: list[MetaEvent] | None = None,
    ) -> Any:
        """
        新的入口方法：直接接收 User 和 Session，不再依赖 Context 里的 Token
        """
        workflow = get_workflow_by_name(session, name, user.id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")

        agent = await self._resolve_agent(workflow, user, session)

        try:
            # 调用 Agent 执行
            result = agent.execute(
                thread_id=thread_id,
                node_name=node_name,
                state=state,
                config=config,
                messages=messages,
                actions=actions,
                meta_events=meta_events,
            )
            return result  # 这里如果是 generator 需要由 Router 处理为 StreamingResponse
        except Exception as error:
            raise AgentExecutionException(name, error) from error

    async def list_agents_for_user(self, user: User, session: Session, workspace_id: UUID | None = None):
        # 简化后的 info 逻辑
        if not workspace_id:
            # 如果业务允许，可以返回空或者默认空间
            return []

        workspace = get_specific_user_workspace(session, user.id, workspace_id)
        if not workspace:
            raise HTTPException(status_code=403, detail="Workspace access denied")

        workflows = list_workflows_by_workspace(session, workspace.id)
        return [
            {
                "name": wf.name,
                "description": wf.description or "",
                "type": "langgraph",
            }
            for wf in workflows
        ]
