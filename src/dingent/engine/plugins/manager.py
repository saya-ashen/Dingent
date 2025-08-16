import json
from pathlib import Path
from typing import Literal

import toml
from fastmcp import Client, FastMCP
from fastmcp.client import UvStdioTransport
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import Tool
from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr

from dingent.engine.backend.resource_manager import get_resource_manager
from dingent.engine.backend.types import ToolOutput
from dingent.utils import find_project_root

from .types import ExecutionModel, PluginUserConfig, export_settings_to_env_dict


class ResourceMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        resource_manager = get_resource_manager()
        result = await call_next(context)
        assert context.fastmcp_context
        tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
        if not result.structured_content or not tool.output_schema:
            try:
                structured_content = json.loads(result.content[0].text)
                result.structured_content = structured_content
            except Exception as e:
                logger.warning(f"Failed to parse structured content: {e}")
                return result
        if {"context", "tool_outputs"}.issubset(result.structured_content.keys()):
            tool_output_dict = result.structured_content["tool_outputs"]
            tool_output = ToolOutput(**tool_output_dict)
            result.structured_content.pop("tool_outputs")
            tool_output_id = resource_manager.register(tool_output)
            result.structured_content["tool_output_id"] = tool_output_id
            result.content[0].text = json.dumps(result.structured_content)
        return result


middleware = ResourceMiddleware()


class PluginInstance:
    mcp_client: Client
    name: str
    _mcp: FastMCP
    _status: Literal["active", "inactive", "error"] = "inactive"

    def __init__(
        self,
        name: str,
        mcp_client: Client,
        mcp: FastMCP,
        status: Literal["active", "inactive", "error"],
    ):
        self.name = name
        self.mcp_client = mcp_client
        self._mcp = mcp
        self._status = status

    @classmethod
    async def create(
        cls,
        manifest: "PluginManifest",
        user_config: PluginUserConfig,
    ) -> "PluginInstance":
        """
        异步工厂方法：创建并完全初始化一个插件实例。
        """
        if not user_config.enabled:
            raise ValueError(f"Plugin '{manifest.name}' is not enabled. This should not happend")
        # 1. 执行原有的同步初始化逻辑来创建 mcp_client
        if manifest.execution.mode == "remote":
            assert manifest.execution.url is not None
            # proxy_client = ProxyClient(manifest.execution.url)
            remote_proxy = FastMCP.as_proxy(manifest.execution.url)
        else:
            assert manifest.execution.script_path
            env = export_settings_to_env_dict(user_config)
            module_path = ".".join(Path(manifest.execution.script_path).with_suffix("").parts)
            transport = UvStdioTransport(
                module_path,
                module=True,
                project_directory=manifest.path.as_posix(),
                env_vars=env,
                with_packages=manifest.dependencies,
                python_version=manifest.python_version,
            )
            # client = Client(transport)
            remote_proxy = FastMCP.as_proxy(transport)

        _status = "inactive"
        try:
            await remote_proxy.get_tools()
            _status = "active"
        except Exception:
            _status = "error"
        mcp = FastMCP(name=user_config.name)
        mcp.mount(remote_proxy)
        mcp.add_middleware(middleware)

        base_tools_dict = await mcp.get_tools()

        # handler tools enabled status
        if not user_config.tools_default_enabled:
            for tool in base_tools_dict.values():
                mirrored_tool = tool.copy()
                mirrored_tool.disable()
                mcp.add_tool(mirrored_tool)

        for tool in user_config.tools or []:
            base_tool = base_tools_dict.get(tool.name)
            if not base_tool:
                continue
            logger.info(f"Translating tool {tool.name} to user config")
            trans_tool = Tool.from_tool(base_tool, name=tool.name, description=tool.description, enabled=tool.enabled)
            mcp.add_tool(trans_tool)
            # If the tool's name changed, we should add a new diabled tool to override original tool
            if tool.name != base_tool.name:
                mirrored_tool = base_tool.copy()
                mirrored_tool.disable()
                mcp.add_tool(mirrored_tool)
            # base_tool.disable()
        mcp_client = Client(mcp)

        instance = cls(name=user_config.name, mcp_client=mcp_client, mcp=mcp, status=_status)

        return instance

    @property
    def status(self):
        return self._status

    async def list_tools(self):
        return await self._mcp.get_tools()


class PluginManifest(BaseModel):
    """ """

    name: str = Field(..., description="插件的唯一标识符")
    version: str | float = Field("0.2.0", description="插件版本 (遵循语义化版本)")
    spec_version: str | float = Field("2.0", description="插件规范版本 (遵循语义化版本)")
    description: str
    execution: ExecutionModel
    dependencies: list[str] | None = None
    python_version: str | None = None
    _plugin_path: Path | None = PrivateAttr(default=None)

    @property
    def path(self) -> Path:
        if self._plugin_path is None:
            raise AttributeError("Plugin path has not been set.")
        return self._plugin_path

    @classmethod
    def from_toml(cls, toml_path: Path) -> "PluginManifest":
        """Loads a plugin manifest from a toml file."""
        if not toml_path.is_file():
            raise FileNotFoundError(f"'plugin.toml' not found at '{toml_path}'")

        plugin_info = toml.load(toml_path)
        plugin_meta = plugin_info.get("plugin", {})
        manifest = cls(**plugin_meta)
        manifest._plugin_path = toml_path.parent
        return manifest

    async def create_instance(
        self,
        user_config: PluginUserConfig,
    ) -> "PluginInstance":
        """
        工厂方法：使用用户配置来创建一个运行时实例。
        """
        if self.path is None:
            raise ValueError("Plugin path is not set. Please set the path before creating an instance.")
        return await PluginInstance.create(
            manifest=self,
            user_config=user_config,
        )


class PluginManager:
    plugins: dict[str, PluginManifest] = {}

    def __init__(self, plugin_dir: str | None = None):
        if not plugin_dir:
            project_root = find_project_root()
            if project_root:
                self.plugin_dir = project_root / "backend" / "plugins"
            else:
                raise ValueError("Plugin directory must be specified or a project root must be found.")
        else:
            self.plugin_dir = Path(plugin_dir)
        if self.plugin_dir:
            logger.info(f"Initializing PluginManager, scanning directory: '{self.plugin_dir}'")
            self._scan_and_register_plugins()

    def _scan_and_register_plugins(self):
        if not self.plugin_dir.is_dir():
            logger.warning(f"Warning: Plugin directory '{self.plugin_dir}' not found.")
            return

        for plugin_path in self.plugin_dir.iterdir():
            if not plugin_path.is_dir():
                logger.warning(f"Skipping '{plugin_path}' as it is not a directory.")
                continue

            toml_path = plugin_path / "plugin.toml"
            if not toml_path.is_file():
                logger.warning(f"Skipping '{plugin_path}' as 'plugin.toml' is missing.")
                continue
            try:
                plugin_manifest = PluginManifest.from_toml(toml_path)
                self.plugins[plugin_manifest.name] = plugin_manifest
            except Exception as e:
                logger.error(f"Error loading plugin from '{plugin_path}': {e}")

    def list_plugins(self) -> dict[str, PluginManifest]:
        return self.plugins

    async def create_instance(self, instance_settings: PluginUserConfig):
        plugin_name = instance_settings.plugin_name
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' is not registered or failed to load.")
        plugin_definition = self.plugins[plugin_name]
        return await plugin_definition.create_instance(instance_settings)


plugin_manager = None


def get_plugin_manager() -> PluginManager:
    global plugin_manager
    if plugin_manager is None:
        plugin_manager = PluginManager()
    return plugin_manager
