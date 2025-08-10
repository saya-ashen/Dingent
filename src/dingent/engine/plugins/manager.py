import json
from pathlib import Path
from typing import Any

import toml
from fastmcp import Client, FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.proxy import ProxyClient
from loguru import logger
from loguru import logger as _logger
from loguru._logger import Logger

from dingent.engine.backend.types import ToolOutput
from dingent.utils import find_project_root

from ..backend.resource_manager import ResourceManager, get_resource_manager
from .types import BasePluginUserConfig, ExecutionModel, PluginSettings

resource_manager = get_resource_manager()


class ResourceMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        assert context.fastmcp_context
        tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
        assert tool.output_schema
        assert result.structured_content
        if {"context", "tool_outputs"}.issubset(result.structured_content.keys()):
            tool_output_dict = result.structured_content["tool_outputs"]
            tool_output = ToolOutput(**tool_output_dict)
            result.structured_content.pop("tool_outputs")
            tool_output_id = resource_manager.register(tool_output)
            result.structured_content["tool_output_id"] = tool_output_id
            result.content[0].text = json.dumps(result.structured_content)
            print("result", result.content[0].text)
        return result

    async def on_message(self, context: MiddlewareContext, call_next):
        """Called for all MCP messages."""
        print(f"Processing {context.method} from {context.source}")

        result = await call_next(context)

        print(f"Completed {context.method}")
        return result


middleware = ResourceMiddleware()


class PluginInstance:
    mcp_client: Client
    name: str

    def __init__(
        self,
        instance_settings: BasePluginUserConfig,
        execution: ExecutionModel,
        resource_manager: ResourceManager | None = None,
        logger: Logger | None = None,
    ):
        self.name = instance_settings.name
        if execution.mode == "remote":
            assert execution.url is not None, "This should not happen."
            remote_proxy = FastMCP.as_proxy(ProxyClient(execution.url))
            mcp = FastMCP(name=self.name)
            mcp.mount(remote_proxy)
            mcp.add_middleware(middleware)
            client = Client(mcp)
            self.mcp_client = client
            self.name = instance_settings.name
        else:
            raise NotImplementedError()

        if logger:
            self.logger = logger
        else:
            self.logger = _logger


class PluginDefinition:
    name: str | None
    description: str = ""
    execution: ExecutionModel
    dependencies: list[str]

    def __init__(
        self,
        settings: PluginSettings,
        **kwargs,
    ) -> None:
        super().__init__()
        self.name = settings.name
        self.description = settings.description
        self.execution = settings.execution
        self.dependencies = settings.dependencies

    def load(self, instance_settings: BasePluginUserConfig):
        return PluginInstance(instance_settings, self.execution)


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
            print(f"Initializing PluginManager, scanning directory: '{self.plugin_dir}'")
            self._scan_and_register_plugins()

    def _scan_and_register_plugins(self):
        if not self.plugin_dir.is_dir():
            print(f"Warning: Plugin directory '{self.plugin_dir}' not found.")
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
                self.plugins[plugin_settings.name] = PluginDefinition(plugin_settings)
            except Exception as e:
                print(f"Error loading plugin from '{plugin_path}': {e}")

    def list_plugins(self) -> dict[str, Any]:
        return self.plugins

    def create_instance(self, instance_settings: BasePluginUserConfig):
        plugin_name = instance_settings.type_name
        if plugin_name not in self.plugins:
            import pdb

            pdb.set_trace()
            raise ValueError(f"Plugin '{plugin_name}' is not registered or failed to load.")
        plugin_definition = self.plugins[plugin_name]
        return plugin_definition.load(instance_settings)
