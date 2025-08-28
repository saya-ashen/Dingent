from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.types import Tool
from pydantic import BaseModel, ValidationError

from .config_manager import ConfigManager
from .plugin_manager import PluginInstance, PluginManager
from .settings import AssistantSettings

logger = logging.getLogger(__name__)


class RunnableTool(BaseModel):
    tool: Tool
    run: Callable[[dict], Any]


class Assistant:
    """
    运行期 Assistant。
    destinations: 当前活动 Workflow 中（经 workflow_manager.instantiate_workflow_assistants 构建后）
                  此 Assistant 可直接到达的下游 Assistant 名称（或 ID）列表。
                  单一活动 Workflow 场景下，可以直接覆盖。
    """

    def __init__(
        self,
        assistant_id: str,
        name: str,
        description: str,
        plugin_instances: dict[str, PluginInstance],
    ):
        self.id = assistant_id
        self.name = name
        self.description = description
        self.plugin_instances = plugin_instances  # key = plugin_name
        self.destinations: list[str] = []

    @classmethod
    async def create(cls, plugin_manager: PluginManager, settings: AssistantSettings) -> Assistant:
        plugin_instances: dict[str, PluginInstance] = {}
        enabled_plugins = [p for p in settings.plugins if p.enabled]
        for pconf in enabled_plugins:
            try:
                inst = await plugin_manager.create_instance(pconf)
                plugin_instances[pconf.plugin_name or pconf.name] = inst
            except Exception as e:
                logger.error(
                    "Create plugin instance failed (assistant=%s plugin=%s): %s",
                    settings.name,
                    getattr(pconf, "plugin_name", pconf.name),
                    e,
                )
                # 可选择：继续 / 或 raise
        return cls(settings.id, settings.name, settings.description or "", plugin_instances)

    @asynccontextmanager
    async def load_tools_langgraph(self):
        """
        返回 langgraph 期望的 tool 列表（普通 Tool 对象）。
        """
        tools: list[Tool] = []
        async with AsyncExitStack() as stack:
            for inst in self.plugin_instances.values():
                client = await stack.enter_async_context(inst.mcp_client)
                session = client.session
                _tools = await load_mcp_tools(session)
                tools.extend(_tools)
            yield tools

    @asynccontextmanager
    async def load_tools(self):
        """
        返回带可直接运行 run(arguments) 的 RunnableTool 列表。
        """
        runnable: list[RunnableTool] = []
        async with AsyncExitStack() as stack:
            for inst in self.plugin_instances.values():
                client = await stack.enter_async_context(inst.mcp_client)
                tools = await client.list_tools()
                for t in tools:

                    async def call_tool(arguments: dict, _client=client, _t=t):
                        return await _client.call_tool(_t.name, arguments=arguments)

                    runnable.append(RunnableTool(tool=t, run=call_tool))
            yield runnable

    async def aclose(self):
        for inst in self.plugin_instances.values():
            try:
                await inst.aclose()
            except Exception as e:
                logger.warning("Error closing plugin instance (assistant=%s): %s", self.name, e)
        self.plugin_instances.clear()


class AssistantManager:
    """
    Assistant 运行期实例管理器（与 ConfigManager 解耦，仅消费其数据）：

    - 负责按需（Lazy）创建 Assistant 实例（包含插件实例）。
    - 订阅 ConfigManager 的 on_change 事件，自动感知配置变更：
        * 删除的助手 -> 关闭并移除实例
        * 修改的助手（配置 hash 变化）-> 关闭并重建（可配置策略）
        * 新增的助手 -> 不主动创建（按需）
    - 提供 rebuild() 进行全量重建。
    - 提供 refresh_settings() 仅刷新配置映射，不影响现有实例（除非原配置已不存在）。
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        plugin_manager: PluginManager,
        *,
        auto_recreate_on_change: bool = True,
        compare_plugins_only: bool = False,
    ):
        """
        auto_recreate_on_change: True 则当 assistant 配置有变化时（基于 hash 比较）自动重建实例
        compare_plugins_only: True 则仅当插件相关配置变化时才重建（忽略描述、名称变更）
        """
        self._config_manager = config_manager
        self._plugin_manager = plugin_manager

        self._assistants: dict[str, Assistant] = {}
        self._settings_map: dict[str, AssistantSettings] = {}
        self._settings_hash: dict[str, str] = {}

        self._lock = asyncio.Lock()
        self._auto_recreate = auto_recreate_on_change
        self._compare_plugins_only = compare_plugins_only

        self._load_settings_initial()
        self._config_manager.register_on_change(self._on_config_change)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _load_settings_initial(self):
        settings_list = self._config_manager.list_assistants()
        self._settings_map = {s.id: s for s in settings_list}
        self._settings_hash = {s.id: self._hash_settings(s) for s in settings_list}

    def _hash_settings(self, s: AssistantSettings) -> str:
        """
        计算一个轻量 hash，用于判断 assistant 配置是否变化。
        若 compare_plugins_only = True，则仅基于插件列表及其字段。
        """
        if self._compare_plugins_only:
            payload = [
                (
                    p.plugin_name or p.name,
                    p.enabled,
                    p.tools_default_enabled,
                    sorted(p.tools or []),
                    sorted(p.config.keys()) if p.config else None,
                )
                for p in sorted(s.plugins, key=lambda x: (x.plugin_name or x.name))
            ]
        else:
            payload = s.model_dump(mode="json", exclude_none=True)
        import hashlib
        import json

        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _build_assistant_instance(self, settings: AssistantSettings) -> Assistant:
        return await Assistant.create(self._plugin_manager, settings)

    async def _maybe_recreate_assistant(self, assistant_id: str, new_settings: AssistantSettings):
        """
        根据 hash 判断是否需要重建。
        """
        old_hash = self._settings_hash.get(assistant_id)
        new_hash = self._hash_settings(new_settings)
        self._settings_map[assistant_id] = new_settings
        self._settings_hash[assistant_id] = new_hash

        if assistant_id not in self._assistants:
            return  # lazy，不自动创建

        if not self._auto_recreate:
            return

        if old_hash == new_hash:
            return

        # 配置变更 -> 重建
        old_instance = self._assistants.pop(assistant_id, None)
        if old_instance:
            try:
                await old_instance.aclose()
            except Exception as e:
                logger.warning("Error closing old assistant '%s' during recreate: %s", assistant_id, e)
        if new_settings.enabled:
            try:
                new_inst = await self._build_assistant_instance(new_settings)
                self._assistants[assistant_id] = new_inst
                logger.info("Assistant '%s' recreated due to config change.", new_settings.name)
            except Exception as e:
                logger.error("Failed to recreate assistant '%s': %s", new_settings.name, e)

    async def _on_config_change(self, old_settings, new_settings):
        """
        ConfigManager on_change 回调（同步调用） -> 这里封装成异步处理。
        old_settings/new_settings 为 AppSettings。
        我们只关心 assistants 列表。
        """
        # 将同步回调切换到异步任务（避免阻塞 ConfigManager 保存流程）
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._handle_config_change_async(old_settings, new_settings))
        except RuntimeError:
            # 没有 event loop（可能在同步上下文） -> 直接运行（阻塞）
            asyncio.run(self._handle_config_change_async(old_settings, new_settings))

    async def _handle_config_change_async(self, old_app, new_app):
        async with self._lock:
            new_map = {a.id: a for a in new_app.assistants}
            old_ids = set(self._settings_map.keys())
            new_ids = set(new_map.keys())

            removed = old_ids - new_ids
            added = new_ids - old_ids
            kept = old_ids & new_ids

            # 关闭已删除的
            for rid in removed:
                inst = self._assistants.pop(rid, None)
                self._settings_map.pop(rid, None)
                self._settings_hash.pop(rid, None)
                if inst:
                    try:
                        await inst.aclose()
                        logger.info("Assistant instance closed (removed) id=%s", rid)
                    except Exception as e:
                        logger.warning("Error closing removed assistant %s: %s", rid, e)

            # 新增
            for nid in added:
                self._settings_map[nid] = new_map[nid]
                self._settings_hash[nid] = self._hash_settings(new_map[nid])
                # 不立即创建实例（lazy）
                logger.info("Assistant settings added id=%s name=%s", nid, new_map[nid].name)

            # 保留 & 可能重建
            for kid in kept:
                await self._maybe_recreate_assistant(kid, new_map[kid])

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def get_assistant(self, assistant_id: str) -> Assistant:
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

    async def get_all_assistants(self, *, only_enabled: bool = True, preload: bool = False) -> dict[str, Assistant]:
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
                            logger.error("Preload assistant '%s' failed: %s", aid, e)
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
                        logger.error("Preload assistant '%s' failed: %s", aid, e)

    async def rebuild(self):
        """
        全量重建：关闭所有已加载实例，重新读取全部 settings，并保持 lazy。
        （如果希望全部立即创建，可以 rebuild() 后再调用 preload()）
        """
        async with self._lock:
            await self._close_all_locked()
            self._load_settings_initial()
            logger.info("AssistantManager rebuild completed. assistants=%d", len(self._settings_map))

    async def refresh_settings_only(self):
        """
        仅刷新配置映射，不关闭已存在实例（如果其 id 仍存在）。
        已删除的 assistant 会被关闭。
        """
        async with self._lock:
            new_list = self._config_manager.list_assistants()
            new_map = {a.id: a for a in new_list}
            # 关闭被删除的
            removed = set(self._settings_map.keys()) - set(new_map.keys())
            for rid in removed:
                inst = self._assistants.pop(rid, None)
                if inst:
                    try:
                        await inst.aclose()
                    except Exception as e:
                        logger.warning("Error closing removed assistant %s: %s", rid, e)
                self._settings_hash.pop(rid, None)
            # 更新/新增
            for aid, aset in new_map.items():
                self._settings_map[aid] = aset
                self._settings_hash[aid] = self._hash_settings(aset)
            logger.info("Assistant settings refreshed. total=%d removed=%d", len(self._settings_map), len(removed))

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
                logger.warning("Error closing assistant %s: %s", assistant_id, e)
            return True

    async def aclose(self):
        async with self._lock:
            await self._close_all_locked()

    async def _close_all_locked(self):
        for inst in self._assistants.values():
            try:
                await inst.aclose()
            except Exception as e:
                logger.warning("Error closing assistant %s: %s", inst.name, e)
        self._assistants.clear()

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

    # ------------------------------------------------------------------ #
    # Exposed Queries for UI / API
    # ------------------------------------------------------------------ #
    def list_assistant_settings(self, *, only_enabled: bool = False) -> list[AssistantSettings]:
        """
        返回当前缓存的 settings 副本（不访问磁盘）。
        """
        result = []
        for s in self._settings_map.values():
            if only_enabled and not s.enabled:
                continue
            result.append(s.model_copy(deep=True))
        return result

    def get_assistant_settings(self, assistant_id: str) -> AssistantSettings | None:
        s = self._settings_map.get(assistant_id)
        return s.model_copy(deep=True) if s else None

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #
    def detach(self):
        """
        从 ConfigManager 取消订阅（若生命周期结束）。
        """
        try:
            self._config_manager.unregister_on_change(self._on_config_change)  # type: ignore[arg-type]
        except Exception:
            pass
