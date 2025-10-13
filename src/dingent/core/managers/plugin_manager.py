import json
import logging
import shutil
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlmodel import Session
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult as FastMCPToolResult
from mcp.types import TextContent

from dingent.core.db.models import AssistantPluginLink, Resource
from dingent.core.runtime.plugin import PluginRuntime
from dingent.core.schemas import PluginManifest
from dingent.core.services.plugin_registry import PluginRegistry
from dingent.core.types import ToolResult

from .resource_manager import ResourceManager

LOGGING_LEVEL_MAP = logging.getLevelNamesMapping()


class ResourceMiddleware(Middleware):
    """
    拦截工具调用结果，标准化为 ToolResult，并存储，仅向模型暴露最小必要文本。
    """

    def __init__(self, session: Session, user_id: UUID, resource_manager: ResourceManager, log_method: Callable):
        super().__init__()
        self.user_id = user_id
        self.session = session
        self.resource_manager = resource_manager
        self.log_with_context = log_method

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        result = await call_next(context)

        assert context.fastmcp_context

        # 1. 抽取原始返回
        raw_text = ""
        if result.content and result.content[0].text:  # type:ignore
            raw_text = result.content[0].text  # type:ignore

        structured = result.structured_content
        parsed_obj: Any = None

        # 2. 尝试解析 JSON
        if structured and isinstance(structured, dict):
            parsed_obj = structured
        else:
            if raw_text:
                try:
                    parsed_obj = json.loads(raw_text)
                except Exception:
                    parsed_obj = raw_text
            else:
                parsed_obj = raw_text

        # 3. 标准化为 ToolResult
        try:
            tool_result = ToolResult.from_any(parsed_obj)
        except Exception as e:
            self.log_with_context("warning", "Failed to parse tool result: {error_msg}", context={"error_msg": f"{e}"})
            tool_result = ToolResult.from_any(raw_text)

        # 4. 注册资源
        resource_to_save = Resource(
            user_id=self.user_id,
            model_text=tool_result.model_text,
            display=[p.model_dump() for p in tool_result.display],
            data=tool_result.data,
            version=tool_result.version,
        )
        artifact_id = str(self.resource_manager.create(resource_to_save, self.session).id)

        # 5. 构建最小结构，喂给模型的文本直接用 model_text
        minimal_struct = {
            "artifact_id": artifact_id,
            "model_text": tool_result.model_text,
            "version": tool_result.version,
        }

        # 6. 覆盖返回
        result.structured_content = minimal_struct
        # 给模型的自然语言部分：只放 model_text，避免输出 JSON 杂讯
        if result.content:
            result.content[0].text = tool_result.model_text  # type:ignore
        else:
            # 部分 fastmcp 实现可能需要确保 content 不为空

            result.content = [
                FastMCPToolResult(content=TextContent(type="text", text=tool_result.model_text)),  # type:ignore
            ]

        return result


class PluginManager:
    """
    Manages the discovery, database synchronization, and runtime lifecycle of plugins.
    The PluginManager acts as the primary bridge between the static plugin code on the
    filesystem and the application's runtime environment. It is not concerned with
    how individual Assistants are configured, but rather with the availability and
    operational state of the plugins themselves.

    Its core responsibilities are:
    1.  **Discovery:** Scans the plugin directory at startup to find all available
        plugins by reading their `plugin.toml` manifest files.
    2.  **Synchronization:** Synchronizes the discovered plugin manifests with the
        `Plugin` table in the database, ensuring the application has a consistent
        registry of all available plugins.
    3.  **Instantiation (Factory):** Acts as a factory for creating `PluginRuntime`
        objects. It takes per-assistant configuration (via an `AssistantPluginLink`)
        and is responsible for launching local plugin processes or connecting
        to remote plugin endpoints.
    """

    def __init__(
        self,
        plugin_registry: PluginRegistry,
        resource_manager: ResourceManager,
        log_manager,
    ):
        self.log_manager = log_manager
        self.registry = plugin_registry
        self.resource_manager = resource_manager
        # user_id -> ResourceMiddleware
        # self.middlewares: dict[str, ResourceMiddleware] = {}  # ResourceMiddleware(session, user_id, resource_manager, self.log_manager.log_with_context)
        self.middlewares = {}
        self._active_runtimes: dict[str, PluginRuntime] = {}

    def list_visible_plugins(self) -> list[PluginManifest]:
        """
        Gets all manifests from the registry and filters them based on
        the current user's permissions.
        (Permission logic is a placeholder for now.)
        """
        manifests = self.registry.get_all_manifests()
        # TODO: apply permission filter by user_id if needed
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

    async def _get_runtime_plugin(
        self,
        *,
        user_id: UUID,
        session: Session,
        plugin_id: str,
        link: AssistantPluginLink,
    ) -> PluginRuntime:
        manifest = self.registry.find_manifest(plugin_id)
        if not manifest:
            raise ValueError(f"Plugin with ID '{plugin_id}' not found in registry.")
        middleware = self.middlewares.get(str(user_id))
        if not middleware:
            middleware = ResourceMiddleware(session, user_id, self.resource_manager, self.log_manager.log_with_context)
            self.middlewares[str(user_id)] = middleware
        return await PluginRuntime.from_config(
            manifest=manifest,
            link=link,
            middleware=middleware,
            log_method=self.log_manager.log_with_context,
        )

    def get_manifest_plugin(self, *, plugin_id: str) -> PluginManifest | None:
        return self.registry.find_manifest(plugin_id)

    def delete_plugin(self, *, plugin_id: str):
        manifest = self.registry.find_manifest(plugin_id)
        if manifest:
            removed = self.registry.remove_manifest_by_id(plugin_id)
            plugin_path = manifest.path
            shutil.rmtree(plugin_path)
            # self.log_manager.log_with_context("info", "Plugin '{plugin}' ({id}) removed.", context={"plugin": plugin.name, "id": plugin_id})
        else:
            # self.log_manager.log_with_context("warning", "Plugin with ID '{id}' not found in PluginManager.", context={"id": plugin_id})
            removed = False
        return removed

    def get_installed_versions(self) -> dict[str, str]:
        """
        Scans registered plugins and returns a dictionary of their IDs and versions.

        Returns:
            A dictionary mapping plugin_id to its version string.
            Example: {"my-cool-plugin": "1.2.0", "another-plugin": "0.9.1"}
        """
        return {}
        # if not self.plugins:
        #     return {}
        #
        # Use a dictionary comprehension for a clean and efficient implementation
        # return {plugin_id: str(manifest.version) for plugin_id, manifest in self.plugins.items() if manifest.version is not None}
