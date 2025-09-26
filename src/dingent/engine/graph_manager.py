from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

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
    # 新增字段用于优雅地处理并发
    build_event: asyncio.Event | None = field(default=None, repr=False)


class GraphBuilder:
    def __init__(self, db_path: Path, app_context: AppContext):
        self._app_ctx = app_context
        self.log_manager = self._app_ctx.log_manager

    async def build(self, workflow_id: str, stack: AsyncExitStack, epoch: int) -> GraphCacheEntry:
        """根据 workflow_id 决定并执行具体的构建逻辑。"""
        workflow = self._app_ctx.workflow_manager.get_workflow(workflow_id)
        # 检查 workflow 是否有效且有起始节点
        if workflow and next((n for n in workflow.nodes if n.data.isStart), None):
            try:
                # 尝试构建完整的工作流图
                return await self._build_workflow_graph(workflow_id, workflow, stack, epoch)
            except Exception as e:
                self.log_manager.log_with_context(
                    "error",
                    "Failed to build workflow graph, falling back to basic. Error: {err}",
                    context={"wf": workflow_id, "err": str(e)},
                )
                # 构建失败，必须关闭当前 stack 并创建一个新的，以防资源泄露
                await stack.aclose()
                new_stack = AsyncExitStack()
                return await self._build_basic_graph(new_stack, epoch)
        else:
            # 如果 workflow 无效或不存在，构建基础图
            if workflow_id != "__basic__":
                self.log_manager.log_with_context(
                    "warning",
                    "Workflow invalid or not found, falling back to basic.",
                    context={"wf": workflow_id},
                )
            return await self._build_basic_graph(stack, epoch)

    async def _build_basic_graph(self, stack: AsyncExitStack, epoch: int) -> GraphCacheEntry:
        """构建一个基础的回退图 (basic fallback graph)。"""
        workflow_id = "__basic__"
        self.log_manager.log_with_context("info", "Building basic fallback graph.", context={"wf": workflow_id})

        llm = self._app_ctx.llm_manager.get_llm(**self._app_ctx.config_manager.get_settings().llm.model_dump())
        graph = StateGraph(MainState)

        def basic_chatbot(state: MainState):
            return {"messages": [llm.invoke(state["messages"])]}

        graph.add_node("basic_chatbot", basic_chatbot)
        graph.add_edge(START, "basic_chatbot")
        graph.add_edge("basic_chatbot", END)

        db_path = self._app_ctx.database_manager.db_path.as_posix()
        checkpointer = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(db_path))

        compiled = graph.compile(checkpointer)
        compiled.name = "agent"

        return GraphCacheEntry(
            workflow_id=workflow_id,
            graph=compiled,
            stack=stack,
            checkpointer=checkpointer,
            default_active_agent=None,
            epoch=epoch,
        )

    async def _build_workflow_graph(self, workflow_id: str, workflow, stack: AsyncExitStack, epoch: int) -> GraphCacheEntry:
        """根据给定的 workflow 定义构建一个完整的 langgraph-swarm 图。"""
        self.log_manager.log_with_context("info", "Building graph for workflow.", context={"wf": workflow_id})

        start_node = next((n for n in workflow.nodes if n.data.isStart), None)
        if not start_node:
            raise ValueError(f"Workflow '{workflow_id}' has no start node.")

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

        db_path = self._app_ctx.database_manager.db_path.as_posix()
        checkpointer = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(db_path))

        compiled_graph = outer.compile(checkpointer)
        compiled_graph.name = "agent"

        return GraphCacheEntry(
            workflow_id=workflow_id,
            graph=compiled_graph,
            stack=stack,
            checkpointer=checkpointer,
            default_active_agent=default_active_agent,
            epoch=epoch,
        )


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
        self._db_manager = app_context.database_manager
        self._cache: dict[str, GraphCacheEntry] = {}
        self._lock = asyncio.Lock()
        self._pending_tasks: dict[str, asyncio.Task] = {}

        self._app_ctx.config_manager.register_on_change(self._on_config_change)
        self._app_ctx.workflow_manager.register_callback(self._on_workflow_change)
        self._rebuild_callbacks: list[Callable[[str, CompiledStateGraph], Awaitable[None]]] = []
        self.log_manager = self._app_ctx.log_manager
        self._builder = GraphBuilder(self._db_manager.db_path, app_context)
        self._global_epoch = 0

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

    async def _cleanup_entry_resources(self, entry: GraphCacheEntry):
        """安全地关闭并清理旧缓存条目的资源。"""
        try:
            await entry.stack.aclose()
        except Exception as e:
            self.log_manager.log_with_context("warning", "Failed to close old resource stack: {err}", context={"err": str(e), "wf": entry.workflow_id})

    async def _rebuild_internal(self, workflow_id: str, reason: str) -> GraphCacheEntry:
        """
        核心图构建与缓存管理方法。
        采用 asyncio.Event 处理并发，并将具体构建逻辑委托给 GraphBuilder。
        """
        async with self._lock:
            entry = self._cache.get(workflow_id)

            # Case 1: 另一个任务正在构建，优雅地等待它完成
            if entry and entry.building:
                build_event = entry.build_event
                # 必须先释放锁，才能 await 事件，避免死锁
                if build_event:
                    self.log_manager.log_with_context("debug", "Waiting for another build task.", context={"wf": workflow_id})
                    self._lock.release()
                    try:
                        await build_event.wait()
                    finally:
                        # 重新获取锁，以便安全地访问缓存
                        await self._lock.acquire()

                # 构建已完成，重新从缓存中获取最新的 entry
                # 如果它又变 dirty 了，下一轮的 _ensure_entry 会处理
                return self._cache[workflow_id]

            # Case 2: 我是第一个构建任务，开始构建流程
            self.log_manager.log_with_context("info", "Starting to build graph.", context={"wf": workflow_id, "reason": reason})
            old_entry = entry

            # 创建一个临时的占位符 entry，并标记为正在构建
            placeholder_entry = GraphCacheEntry(
                workflow_id=workflow_id,
                graph=old_entry.graph if old_entry else None,  # type: ignore
                stack=old_entry.stack if old_entry else AsyncExitStack(),  # type: ignore
                checkpointer=old_entry.checkpointer if old_entry else None,
                default_active_agent=old_entry.default_active_agent if old_entry else None,
                building=True,
                build_event=asyncio.Event(),
            )
            self._cache[workflow_id] = placeholder_entry

        # --- 锁已释放，可以安全地执行耗时的I/O和计算操作 ---
        new_entry = None
        try:
            # 步骤 1: 如果存在旧的、需要被替换的条目，清理其资源
            if old_entry:
                await self._cleanup_entry_resources(old_entry)

            # 步骤 2: 创建一个新的资源栈用于本次构建
            new_stack = AsyncExitStack()

            # 步骤 3: 委托给 GraphBuilder 来执行实际的构建逻辑
            new_entry = await self._builder.build(workflow_id, new_stack, self._global_epoch)

            # 步骤 4: 构建完成，用新的 entry 原子化地更新缓存
            async with self._lock:
                self._cache[workflow_id] = new_entry

            self.log_manager.log_with_context("info", "Workflow graph built successfully.", context={"wf": workflow_id})

            # 步骤 5: 触发构建完成后的回调
            if self._rebuild_callbacks:
                self.log_manager.log_with_context("info", "Triggering rebuild callbacks.", context={"wf": workflow_id})
                callbacks = [cb(workflow_id, new_entry.graph) for cb in self._rebuild_callbacks]
                asyncio.gather(*callbacks)

            return new_entry

        except Exception as e:
            # 异常处理：构建失败也需要更新缓存状态
            self.log_manager.log_with_context("error", "Graph build failed unexpectedly: {err}", context={"err": str(e), "wf": workflow_id})
            # 如果有新条目（部分成功），则用它；否则保留占位符但标记为非构建中
            final_entry = new_entry or placeholder_entry
            async with self._lock:
                self._cache[workflow_id] = final_entry
            raise e  # 重新抛出异常，让调用者知道失败了

        finally:
            # 步骤 6: 无论成功与否，都标记构建结束并通知所有等待者
            async with self._lock:
                # 获取最终的 entry，可能是新构建的，也可能是占位符
                if final_entry := self._cache.get(workflow_id):
                    final_entry.building = False
                    if build_event := final_entry.build_event:
                        build_event.set()
                        final_entry.build_event = None  # 清理事件对象

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
