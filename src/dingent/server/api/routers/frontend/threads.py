from __future__ import annotations
import os
import asyncio
from dataclasses import dataclass
from typing import Awaitable, OrderedDict, cast
from copilotkit import Agent, CopilotKitContext, LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from copilotkit.sdk import CopilotKitRemoteEndpoint
from fastapi import APIRouter, Depends, FastAPI
from fastapi.exceptions import HTTPException
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import Engine
from sqlmodel import Session

from dingent.core.factories.graph_factory import GraphArtifact, GraphFactory
from dingent.core.managers.llm_manager import LLMManager
from time import time
from dingent.server.auth.authorization import dynamic_authorizer
from dingent.server.auth.security import get_current_user_from_token
from dingent.server.copilot.add_fastapi_endpoint import add_fastapi_endpoint
from dingent.server.copilot.agents import FixedLangGraphAgent
from dingent.core.db.crud.workflow import get_workflow_by_name
from dingent.server.copilot.async_copilotkit_remote_endpoint import AsyncCopilotKitRemoteEndpoint

router = APIRouter(dependencies=[Depends(dynamic_authorizer)])


MAX_CACHE_SIZE = 128


from collections import OrderedDict
from dataclasses import dataclass
from time import time
from typing import Tuple, Any, Callable
import threading

Key = Tuple[str, str]  # (user_id, agent_name) or (workflow_id, ...)


@dataclass
class GraphCacheEntry:
    graph: GraphArtifact
    version: str
    built_at: float


class GraphCache:
    def __init__(self, maxsize: int = 128):
        self._store: OrderedDict[Key, GraphCacheEntry] = OrderedDict()
        self._locks: dict[Key, threading.Lock] = {}
        self._global_lock = threading.RLock()
        self._maxsize = maxsize

    def _get_lock(self, key: Key) -> threading.Lock:
        with self._global_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._maxsize:
            # pop least-recently-used (front)
            key, _ = self._store.popitem(last=False)
            self._locks.pop(key, None)

    async def get_or_build(
        self,
        key: Key,
        version: str,
        builder: Callable[[], Awaitable[GraphArtifact]],  # returns either graph or an object with `.graph`
    ) -> GraphArtifact:
        # Fast path: try without locking (LRU move needs lock)
        with self._global_lock:
            entry = self._store.get(key)
            if entry and entry.version == version:
                self._store.move_to_end(key)  # mark as recently used
                return entry.graph

        # Per-key build lock to prevent duplicate builds
        lock = self._get_lock(key)
        with lock:
            # Double-check inside the lock
            with self._global_lock:
                entry = self._store.get(key)
                if entry and entry.version == version:
                    self._store.move_to_end(key)
                    return entry.graph

            # Build outside global lock
            built = await builder()
            graph = getattr(built, "graph", built)
            new_entry = GraphCacheEntry(graph=graph, version=version, built_at=time())

            # Commit + LRU maintenance
            with self._global_lock:
                self._store[key] = new_entry
                self._store.move_to_end(key)
                self._evict_if_needed()

            return graph

    def invalidate(self, key: Key) -> None:
        with self._global_lock:
            self._store.pop(key, None)
            self._locks.pop(key, None)

    def clear(self) -> None:
        with self._global_lock:
            self._store.clear()
            self._locks.clear()


def ensure_graph_cache(app) -> GraphCache:
    if not hasattr(app.state, "graph_cache"):
        app.state.graph_cache = GraphCache(maxsize=MAX_CACHE_SIZE)
    return app.state.graph_cache


def setup_copilot_router(app: FastAPI, graph_factory: GraphFactory, engine: Engine, checkpointer):
    """
    Creates and configures the secure router for CopilotKit and adds it to the application.

    This function is called from within the lifespan manager after the SDK has been initialized.
    """
    print("--- Setting up CopilotKit Secure Router ---")

    # HACK: llm manager
    llm_manager = LLMManager()
    api_key = os.getenv("OPENAI_API_KEY")
    llm = llm_manager.get_llm(
        model_provider="openai",
        model="gpt-4.1",
        api_base="https://www.dmxapi.cn/v1",
        api_key=api_key,
    )

    async def _agents_pipeline(context: CopilotKitContext, name: str) -> Agent:
        token = context.get("properties", {}).get("authorization")

        if not token:
            raise HTTPException(status_code=401, detail="Missing token")

        with Session(engine, expire_on_commit=False) as session:
            user = get_current_user_from_token(session, token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid token")

            workflow = get_workflow_by_name(session, name, user.id)
            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
            artifact = await graph_factory.build(workflow, llm, checkpointer)
            return FixedLangGraphAgent(
                name=workflow.name,
                description=f"Agent for workflow '{workflow.name}'",
                graph=artifact.graph,
                langgraph_config={"token": token} if token else {},
            )

    sdk = AsyncCopilotKitRemoteEndpoint(agent_factory=_agents_pipeline, engine=engine)
    app.state.copilot_sdk = sdk
    add_fastapi_endpoint(router, sdk, "/copilotkit")

    app.include_router(router, prefix="/api/v1/frontend")

    print("--- CopilotKit Secure Router has been added to the application ---")
