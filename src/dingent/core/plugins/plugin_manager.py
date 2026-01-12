import logging
import shutil

from fastmcp.server.middleware import Middleware, MiddlewareContext

from .plugin import PluginRuntime
from .plugin_registry import PluginRegistry
from .schemas import PluginConfigSchema, PluginManifest

LOGGING_LEVEL_MAP = logging.getLevelNamesMapping()


class ConfigMiddleware(Middleware):
    """
    拦截工具调用结果，标准化为 ToolResult，并存储，仅向模型暴露最小必要文本。
    """

    def __init__(self, config_schema: PluginConfigSchema):
        super().__init__()

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        return await call_next(context)


class PluginManager:
    def __init__(
        self,
        plugin_registry: PluginRegistry,
        log_manager,
    ):
        self.log_manager = log_manager
        self.registry = plugin_registry
        self.middlewares = {}
        self._active_runtimes: dict[str, PluginRuntime] = {}

    def list_visible_plugins(self) -> list[PluginManifest]:
        """
        Gets all manifests from the registry and filters them based on
        the current user's permissions.
        (Permission logic is a placeholder for now.)
        """
        manifests = self.registry.get_all_manifests()
        return manifests

    async def get_or_create_runtime(self, plugin_registry_id: str) -> PluginRuntime:
        """
        Gets the singleton runtime instance for a plugin, creating it if it doesn't exist.
        This method is thread-safe for creation due to Python's GIL, but for async
        environments, a lock might be considered for production-grade robustness.
        """
        # 1. 检查缓存中是否已有实例
        if plugin_registry_id in self._active_runtimes:
            return self._active_runtimes[plugin_registry_id]

        # 2. 如果没有，则创建新实例
        self.log_manager.log_with_context("info", f"Creating singleton instance for plugin '{plugin_registry_id}'.")
        manifest = self.registry.find_manifest(plugin_registry_id)
        if not manifest:
            raise ValueError(f"Plugin with ID '{plugin_registry_id}' not found in registry.")

        runtime_instance = await PluginRuntime.create_singleton(
            manifest=manifest,
            log_method=self.log_manager.log_with_context,
        )

        # 3. 存入缓存并返回
        self._active_runtimes[plugin_registry_id] = runtime_instance
        return runtime_instance

    def get_manifest_plugin(self, *, plugin_id: str) -> PluginManifest | None:
        return self.registry.find_manifest(plugin_id)

    def delete_plugin(self, *, plugin_id: str):
        manifest = self.registry.find_manifest(plugin_id)
        if manifest:
            removed = self.registry.remove_manifest_by_id(plugin_id)
            plugin_path = manifest.path
            shutil.rmtree(plugin_path)
        else:
            removed = False
        return removed

    async def reload_plugins(self):
        self.registry.reload_plugins()
