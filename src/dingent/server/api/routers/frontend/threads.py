from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import OrderedDict, cast
from copilotkit.integrations.fastapi import add_fastapi_endpoint
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
from dingent.server.copilot.agents import FixedLangGraphAgent, LazyFixedLangGraphAgent
from dingent.core.db.crud.workflow import get_workflow_by_name, list_workflows_by_user

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

    def get_or_build(
        self,
        key: Key,
        version: str,
        builder: Callable[[], GraphArtifact],  # returns either graph or an object with `.graph`
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
            built = builder()
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
    llm = llm_manager.get_llm(model_provider="openai", model="gpt-4.1", api_base="https://www.dmxapi.cn/v1")

    def _agents_pipeline(context: CopilotKitContext) -> list[Agent]:
        # 1) 认证（注意：不再依赖 frontend_url 推断 name）
        token = context.get("properties", {}).get("authorization")
        graph_cache = ensure_graph_cache(app)

        if not token:
            # 按你原有逻辑决定：返回空/抛 401
            return []

        with Session(engine, expire_on_commit=False) as session:
            user = get_current_user_from_token(session, token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid token")

            # 2) 列出该用户的所有 workflows，逐个包装成 Lazy 代理
            workflows = list_workflows_by_user(session, user.id)  # <- 你提到可用的接口

            def make_lazy_agent(wf) -> LazyFixedLangGraphAgent:
                # 缓存 key / 版本：建议用 (user_id, workflow_id)
                key = (str(user.id), str(wf.id))
                version = str(wf.updated_at)  # 更新即失效

                def builder():
                    # 缓存里拿 graph，不存在则 build_sync
                    def build_artifact():
                        breakpoint()
                        artifact = graph_factory.build_sync(wf, llm, checkpointer)
                        breakpoint()
                        return artifact

                    graph_art = graph_cache.get_or_build(key, version, build_artifact)

                    # 命中后才真正实例化 FixedLangGraphAgent
                    return FixedLangGraphAgent(
                        name=wf.name,
                        description=f"Agent for workflow '{wf.name}'",
                        graph=graph_art.graph,
                        langgraph_config={"token": token} if token else {},
                    )

                return LazyFixedLangGraphAgent(
                    name=wf.name,
                    description=f"Agent for workflow '{wf.name}' (lazy)",
                    builder=builder,
                )

            # 3) 返回“仅含 name 的懒代理”列表；你的两行筛选代码只会读 name，不会触发构建
            return cast(list[Agent], [make_lazy_agent(wf) for wf in workflows])

    sdk = CopilotKitRemoteEndpoint(agents=_agents_pipeline)
    app.state.copilot_sdk = sdk
    add_fastapi_endpoint(cast(FastAPI, router), sdk, "/copilotkit")

    app.include_router(router, prefix="/api/v1/frontend")

    print("--- CopilotKit Secure Router has been added to the application ---")

    # add_langgraph_fastapi_endpoint(
    #     app=cast(FastAPI, router),
    #     agent=LangGraphAGUIAgent(
    #         name="sample_agent",  # the name of your agent defined in langgraph.json
    #         description="Describe your agent here, will be used for multi-agent orchestration",
    #         graph=graph,  # the graph object from your langgraph import
    #     ),
    #     path="/copilotkit",
    # )
