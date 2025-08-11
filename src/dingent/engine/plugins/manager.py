import json
from pathlib import Path

import toml
from fastmcp import Client, FastMCP
from fastmcp.client import UvStdioTransport
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.proxy import ProxyClient
from loguru import logger
from loguru import logger as _logger
from loguru._logger import Logger

from dingent.engine.backend.resource_manager import get_resource_manager
from dingent.engine.backend.types import ToolOutput
from dingent.utils import find_project_root

from .types import BasePluginSettings, ExecutionModel, PluginSettings, export_settings_to_env_dict


class ResourceMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        resource_manager = get_resource_manager()
        result = await call_next(context)
        assert context.fastmcp_context
        tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
        if not result.structured_content or not tool.output_schema:
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

    def __init__(
        self,
        instance_settings: BasePluginSettings,
        execution: ExecutionModel,
        plugin_path: str,
        logger: Logger | None = None,
        dependencies: list[str] | None = None,
        python_version: str | None = None,
    ):
        self.name = instance_settings.name
        if execution.mode == "remote":
            assert execution.url is not None, "This should not happen."
            remote_proxy = FastMCP.as_proxy(ProxyClient(execution.url))
        else:
            assert execution.script_path
            env = export_settings_to_env_dict(instance_settings)
            project_path = Path(plugin_path).parent.parent
            plugin_folder = Path(plugin_path).name
            module_path = ".".join(Path(execution.script_path).with_suffix("").parts)
            transport = UvStdioTransport(
                f"plugins.{plugin_folder}.{module_path}",
                module=True,
                project_directory=project_path.as_posix(),
                env_vars=env,
                with_packages=dependencies,
                python_version=python_version,
            )
            client = Client(transport)
            remote_proxy = FastMCP.as_proxy(client)
        mcp = FastMCP(name=self.name)
        mcp.mount(remote_proxy)
        mcp.add_middleware(middleware)
        client = Client(mcp)
        self.mcp_client = client
        self.name = instance_settings.name

        if logger:
            self.logger = logger
        else:
            self.logger = _logger


class PluginDefinition:
    name: str | None
    description: str = ""
    execution: ExecutionModel
    plugin_path: str
    dependencies: list[str] | None
    python_version: str | None

    def __init__(
        self,
        settings: PluginSettings,
        plugin_path: str,
        **kwargs,
    ) -> None:
        super().__init__()
        self.name = settings.name
        self.description = settings.description
        self.execution = settings.execution
        self.dependencies = settings.dependencies
        self.python_version = settings.python_version
        self.plugin_path = plugin_path

    def load(self, instance_settings: BasePluginSettings):
        return PluginInstance(instance_settings, self.execution, dependencies=self.dependencies, plugin_path=self.plugin_path, python_version=self.python_version)


class PluginManager:
    plugins: dict[str, PluginDefinition] = {}

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
                plugin_info = toml.load(toml_path)
                plugin_meta = plugin_info.get("plugin", {})
                plugin_settings = PluginSettings(**plugin_meta)
                self.plugins[plugin_settings.name] = PluginDefinition(plugin_settings, plugin_path.as_posix())
            except Exception as e:
                print(f"Error loading plugin from '{plugin_path}': {e}")

    def list_plugins(self) -> dict[str, PluginDefinition]:
        return self.plugins

    def create_instance(self, instance_settings: BasePluginSettings):
        plugin_name = instance_settings.plugin_name
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' is not registered or failed to load.")
        plugin_definition = self.plugins[plugin_name]
        return plugin_definition.load(instance_settings)


plugin_manager = None


def get_plugin_manager() -> PluginManager:
    global plugin_manager
    if plugin_manager is None:
        plugin_manager = PluginManager()
    return plugin_manager
