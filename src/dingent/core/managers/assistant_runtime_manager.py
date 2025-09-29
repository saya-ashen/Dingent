from __future__ import annotations

import asyncio
from collections.abc import Iterable
from uuid import UUID

from pydantic import ValidationError
from sqlmodel import Session, select

from dingent.core.db.models import Assistant
from dingent.core.runtime.assistant import AssistantRuntime

from .plugin_manager import PluginManager


class AssistantRuntimeManager:
    """
    This is the orchestrator. Its job is to build a complete, functional product (a running AssistantRuntime)
    When asked to build an AssistantRuntime, it reads the main blueprint (Assistant and its AssistantPluginLinks) from the database.
    It sees that the blueprint requires several specialized parts (the plugins). It then turns to the PluginManager (the specialist) and says, "Here are the instructions (AssistantPluginLink), build me one of these."
    It collects all the running parts from the PluginManager, assembles them into the final AssistantRuntime, and keeps track of it while it's active.
    It never writes to the database. It only reads instructions and manages the in-memory, running state.
    """

    def __init__(
        self,
        session: Session,
        user_id: UUID,
        plugin_manager: PluginManager,
        log_manager,
    ):
        """
        auto_recreate_on_change: True 则当 assistant 配置有变化时（基于 hash 比较）自动重建实例
        compare_plugins_only: True 则仅当插件相关配置变化时才重建（忽略描述、名称变更）
        """
        self._plugin_manager = plugin_manager
        self._log_manager = log_manager

        self._assistants: dict[str, AssistantRuntime] = {}
        self._settings_map: dict[str, Assistant] = {}
        self._settings_hash: dict[str, str] = {}

        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _build_assistant_instance(self, assistant: Assistant) -> AssistantRuntime:
        return await AssistantRuntime.create_runtime(
            self._plugin_manager,
            assistant,
            self._log_manager.log_with_context,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def get_runtime_assistant(self, assistant_id: str) -> AssistantRuntime:
        async with self._lock:
            # settings 存在性 & enabled 检查
            settings = self._settings_map.get(assistant_id)
            if not settings or not settings.enabled:
                raise ValueError(f"Assistant '{assistant_id}' not found or disabled.")

            if assistant_id in self._assistants:
                return self._assistants[assistant_id]

            # 创建新的实例
            try:
                inst = await self._build_assistant_instance(settings)
            except ValidationError as e:
                raise ValueError(f"Assistant settings invalid '{assistant_id}': {e}") from e
            except Exception as e:
                raise RuntimeError(f"Failed to build assistant '{assistant_id}': {e}") from e

            self._assistants[assistant_id] = inst
            return inst

    async def get_all_runtime_assistants(self, *, only_enabled: bool = True, preload: bool = False) -> dict[str, AssistantRuntime]:
        """
        返回（并可选预加载）所有 Assistant 实例。
        preload=True 会为符合条件的配置全部实例化。
        """
        async with self._lock:
            target_ids = [aid for aid, s in self._settings_map.items() if (s.enabled or not only_enabled)]
            if preload:
                for aid in target_ids:
                    if aid not in self._assistants:
                        try:
                            inst = await self._build_assistant_instance(self._settings_map[aid])
                            self._assistants[aid] = inst
                        except Exception as e:
                            self._log_manager.log_with_context("error", "Preload assistant '{name}' failed: {e}", context={"name": self._settings_map[aid].name, "e": e})
            # 仅返回已存在的 & 符合条件的
            return {aid: self._assistants[aid] for aid in target_ids if aid in self._assistants}

    async def preload(self, assistant_ids: Iterable[str] | None = None):
        """
        预加载指定（或全部）助手实例。
        """
        async with self._lock:
            if assistant_ids is None:
                assistant_ids = list(self._settings_map.keys())
            for aid in assistant_ids:
                s = self._settings_map.get(aid)
                if not s or not s.enabled:
                    continue
                if aid not in self._assistants:
                    try:
                        self._assistants[aid] = await self._build_assistant_instance(s)
                    except Exception as e:
                        self._log_manager.log_with_context("error", "Preload assistant '{name}' failed: {e}", context={"name": s.name, "e": e})

    async def close_assistant(self, assistant_id: str) -> bool:
        """
        主动关闭某个实例（不会删除配置），下次访问时会重新创建。
        """
        async with self._lock:
            inst = self._assistants.pop(assistant_id, None)
            if not inst:
                return False
            try:
                await inst.aclose()
            except Exception as e:
                self._log_manager.log_with_context("warning", "Error closing assistant '{id}': {e}", context={"id": assistant_id, "e": e})
            return True

    async def refresh_settings(self, session: Session):
        result = session.exec(select(Assistant)).all()
        async with self._lock:
            # TODO: 存储配置的hash，如果配置发生更改，就更新Assistant
            self._settings_map = {str(a.id): a for a in result}

    # ------------------------------------------------------------------ #
    # Destinations Mutation (供 WorkflowManager 调用)
    # ------------------------------------------------------------------ #
    async def set_destinations(self, mapping: dict[str, list[str]], *, clear_others: bool = True):
        """
        mapping: assistant_id -> destinations 列表
        clear_others: 若 True，未出现在 mapping 中的已加载实例 destinations 清空
        """
        async with self._lock:
            for aid, dests in mapping.items():
                inst = self._assistants.get(aid)
                if inst:
                    inst.destinations = list(dests)
            if clear_others:
                untouched = set(self._assistants.keys()) - set(mapping.keys())
                for aid in untouched:
                    self._assistants[aid].destinations = []
