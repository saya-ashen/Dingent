from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph_swarm import create_swarm

if TYPE_CHECKING:
    from dingent.core.context import AppContext

# 复用 graph.py 中的构建元素
from .graph import (
    MainState,
    _normalize_name,
    create_assistant_graphs,
    get_safe_swarm,
)

CHECKPOINT_ROOT = Path(".dingent/data/checkpoints")


def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)[:80]


@dataclass
class GraphCacheEntry:
    workflow_id: str
    graph: CompiledStateGraph
    stack: AsyncExitStack
    checkpointer: object
    default_active_agent: str | None
    dirty: bool = False
    building: bool = False
    epoch: int = 0


class GraphManager:
    """
    多 workflow 图缓存管理：
      - 按 workflow_id 缓存编译后的 LangGraph
      - 懒加载与按需重建
      - 配置/Workflow 事件触发 dirty 标记
    """

    def __init__(self, app_context: AppContext):
        """
        Initializes the GraphManager with an explicit AppContext.
        """
        self._app_ctx = app_context  # <-- Dependency is now injected
        self._cache: dict[str, GraphCacheEntry] = {}
        self._lock = asyncio.Lock()
        self._pending_tasks: dict[str, asyncio.Task] = {}
        self._global_epoch = 0

        # Subscriptions now use the injected context
        self._app_ctx.config_manager.register_on_change(self._on_config_change)
        self._app_ctx.workflow_manager.register_callback(self._on_workflow_change)
        self._rebuild_callbacks: list[Callable[[str, CompiledStateGraph], Awaitable[None]]] = []
        self.log_manager = self._app_ctx.log_manager

    # ---------------- Public API ----------------
    def _checkpoint_path(self, workflow_id: str) -> Path:
        project_root = self._app_ctx.project_root
        assert project_root is not None, "Project root must be set in AppContext."
        return project_root / CHECKPOINT_ROOT / f"{_slug(workflow_id)}.sqlite"

    async def get_graph(self, workflow_id: str | None = None) -> CompiledStateGraph:
        wid = workflow_id or self._resolve_active_workflow_id() or "__basic__"
        entry = await self._ensure_entry(wid)
        return entry.graph

    async def rebuild_workflow(self, workflow_id: str) -> CompiledStateGraph:
        entry = await self._rebuild_internal(workflow_id, reason="explicit_rebuild")
        return entry.graph

    async def invalidate_workflow(self, workflow_id: str):
        async with self._lock:
            if workflow_id in self._cache:
                self._cache[workflow_id].dirty = True

    async def invalidate_all(self):
        async with self._lock:
            for e in self._cache.values():
                e.dirty = True

    def request_rebuild(self, workflow_id: str, debounce: float = 0.4):
        if workflow_id in self._pending_tasks:
            return

        async def _job():
            try:
                await asyncio.sleep(debounce)
                await self.rebuild_workflow(workflow_id)
            finally:
                self._pending_tasks.pop(workflow_id, None)

        self._pending_tasks[workflow_id] = asyncio.create_task(_job())

    async def close_workflow(self, workflow_id: str):
        async with self._lock:
            entry = self._cache.pop(workflow_id, None)
        if entry:
            try:
                await entry.stack.aclose()
            except Exception as e:
                self.log_manager.log_with_context("warning", "Close workflow graph failed: {err}", context={"err": str(e), "wf": workflow_id})

    async def close_all(self):
        async with self._lock:
            cache = self._cache
            self._cache = {}
        for entry in cache.values():
            try:
                await entry.stack.aclose()
            except Exception as e:
                self.log_manager.log_with_context("warning", "Close workflow graph failed: {err}", context={"err": str(e), "wf": entry.workflow_id})

    def register_rebuild_callback(self, callback: Callable[[str, CompiledStateGraph], Awaitable[None]]):
        """
        Registers an asynchronous callback to be executed after a graph is successfully rebuilt.
        The callback will receive the workflow_id and the new graph instance.
        """
        self._rebuild_callbacks.append(callback)

    # ---------------- Internal Helpers ----------------

    def _resolve_active_workflow_id(self) -> str | None:
        return self._app_ctx.workflow_manager.active_workflow_id

    async def _ensure_entry(self, workflow_id: str) -> GraphCacheEntry:
        async with self._lock:
            entry = self._cache.get(workflow_id)
            if entry and not entry.dirty:
                return entry
        return await self._rebuild_internal(workflow_id, reason="ensure")

    async def _rebuild_internal(self, workflow_id: str, reason: str) -> GraphCacheEntry:
        async with self._lock:
            entry = self._cache.get(workflow_id)
            if entry and entry.building:
                # 等待正在构建的任务
                while entry.building:
                    await asyncio.sleep(0.05)
                if not entry.dirty:
                    return entry
            if not entry:
                entry = GraphCacheEntry(
                    workflow_id=workflow_id,
                    graph=None,  # type: ignore
                    stack=AsyncExitStack(),
                    checkpointer=None,
                    default_active_agent=None,
                )
                self._cache[workflow_id] = entry
            entry.building = True

        try:
            # 关闭旧资源
            if entry.graph is not None:
                try:
                    await entry.stack.aclose()
                except Exception as e:
                    self.log_manager.log_with_context("warning", "Close old stack failed: {err}", context={"err": str(e), "wf": workflow_id})

            stack = AsyncExitStack()

            # 基础 fallback
            if workflow_id == "__basic__":
                llm = self._app_ctx.llm_manager.get_llm(**self._app_ctx.config_manager.get_settings().llm.model_dump())
                graph = StateGraph(MainState)

                def basic_chatbot(state: MainState):
                    return {"messages": [llm.invoke(state["messages"])]}

                graph.add_node("basic_chatbot", basic_chatbot)
                graph.add_edge(START, "basic_chatbot")
                graph.add_edge("basic_chatbot", END)
                saver = InMemorySaver()
                compiled = graph.compile(saver)
                compiled.name = "agent"
                new_entry = GraphCacheEntry(
                    workflow_id=workflow_id,
                    graph=compiled,
                    stack=stack,
                    checkpointer=saver,
                    default_active_agent=None,
                    dirty=False,
                    epoch=self._global_epoch,
                )
                async with self._lock:
                    self._cache[workflow_id] = new_entry
                self.log_manager.log_with_context("info", "Built basic fallback graph.", context={"workflow_id": workflow_id, "reason": reason})
                return new_entry

            workflow = self._app_ctx.workflow_manager.get_workflow(workflow_id)
            if not workflow:
                return await self._rebuild_internal("__basic__", reason="missing_workflow")

            start_node = next((n for n in workflow.nodes if n.data.isStart), None)
            if not start_node:
                self.log_manager.log_with_context("warning", "Workflow missing start node; fallback basic.", context={"workflow_id": workflow_id})
                return await self._rebuild_internal("__basic__", reason="no_start")

            default_active_agent = _normalize_name(start_node.data.assistantName)
            llm = self._app_ctx.llm_manager.get_llm(**self._app_ctx.config_manager.get_settings().llm.model_dump())

            assistants_ctx = create_assistant_graphs(self._app_ctx.workflow_manager, workflow_id, llm, self.log_manager.log_with_context)
            assistants = await stack.enter_async_context(assistants_ctx)

            swarm = create_swarm(
                agents=list(assistants.values()),
                state_schema=MainState,
                default_active_agent=default_active_agent,
                context_schema=dict,
            )
            compiled_swarm = swarm.compile()
            safe_swarm = get_safe_swarm(compiled_swarm, self.log_manager.log_with_context)

            outer = StateGraph(MainState)
            outer.add_node("swarm", safe_swarm)
            outer.add_edge(START, "swarm")
            outer.add_edge("swarm", END)

            cp_path = self._checkpoint_path(workflow_id)
            cp_path.parent.mkdir(parents=True, exist_ok=True)
            # checkpointer = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(cp_path.as_posix()))
            checkpointer = await stack.enter_async_context(
                AsyncSqliteSaver.from_conn_string((self._app_ctx.project_root / ".dingent/data/checkpoints/checkpoint.sqlite").as_posix())
            )
            compiled_graph = outer.compile(checkpointer)
            compiled_graph.name = "agent"

            new_entry = GraphCacheEntry(
                workflow_id=workflow_id,
                graph=compiled_graph,
                stack=stack,
                checkpointer=checkpointer,
                default_active_agent=default_active_agent,
                dirty=False,
                epoch=self._global_epoch,
            )
            async with self._lock:
                self._cache[workflow_id] = new_entry
            self.log_manager.log_with_context(
                "info",
                "Workflow graph built",
                context={"workflow_id": workflow_id, "default_agent": default_active_agent, "reason": reason},
            )
            if self._rebuild_callbacks:
                self.log_manager.log_with_context("info", "Triggering rebuild callbacks for workflow: {wf_id}", context={"wf_id": workflow_id})
                for callback in self._rebuild_callbacks:
                    asyncio.create_task(callback(workflow_id, new_entry.graph))
            return new_entry
        finally:
            async with self._lock:
                self._cache[workflow_id].building = False  # type: ignore

    # ---------------- Event Hooks ----------------

    def _on_config_change(self, old_settings, new_settings):
        try:
            for e in self._cache.values():
                e.dirty = True
            self._global_epoch += 1
            self.log_manager.log_with_context("info", "Config changed -> all graphs dirty.", context={"epoch": self._global_epoch})
            active_wid = self._resolve_active_workflow_id()
            if active_wid and active_wid in self._cache:
                self.log_manager.log_with_context("info", "Proactively rebuilding active workflow due to global config change.", context={"workflow_id": active_wid})
                # Use the existing debounced rebuild request
                self.request_rebuild(active_wid, debounce=0.2)
        except Exception as e:
            self.log_manager.log_with_context("error", "Config change hook error: {err}", context={"err": str(e)})

    def _on_workflow_change(self, event: str, workflow_id: str, _wf):
        try:
            self.log_manager.log_with_context("info", "Workflow event: {event}", context={"event": event, "wf": workflow_id})
            if event == "deleted":
                asyncio.create_task(self.close_workflow(workflow_id))
            elif event in ("updated",):
                asyncio.create_task(self.invalidate_workflow(workflow_id))
                if workflow_id == self._resolve_active_workflow_id():
                    self.log_manager.log_with_context("info", "Proactively rebuilding active workflow because it was updated.", context={"workflow_id": workflow_id})
                    self.request_rebuild(workflow_id, debounce=0.2)
            elif event == "activated":
                self.request_rebuild(workflow_id, debounce=0.05)
        except Exception as e:
            self.log_manager.log_with_context("error", "Workflow change hook error: {err}", context={"err": str(e), "event": event, "wf": workflow_id})
