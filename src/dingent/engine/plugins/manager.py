from pathlib import Path
from typing import Any

import toml
from fastmcp import Client
from fastmcp.client import StreamableHttpTransport
from loguru import logger
from loguru import logger as _logger
from loguru._logger import Logger

from dingent.utils import find_project_root

from .resource_manager import ResourceManager
from .types import BasePluginUserConfig, ExecutionModel, PluginSettings


class PluginInstance:
    mcp_client: Client
    name: str

    def __init__(self, instance_settings: BasePluginUserConfig, execution: ExecutionModel):
        if execution.mode == "remote":
            assert execution.url is not None, "This should not happen."
            transport = StreamableHttpTransport(url=execution.url)
            client = Client(transport)
            self.mcp_client = client
            self.name = instance_settings["name"]
        else:
            raise NotImplementedError()


class PluginDefinition:
    name: str | None
    description: str = ""
    execution: ExecutionModel
    dependencies: list[str]

    def __init__(
        self,
        settings: PluginSettings,
        resource_manager: ResourceManager | None = None,
        logger: Logger | None = None,
        **kwargs,
    ) -> None:
        super().__init__()
        self.resource_manager = resource_manager
        self.name = settings.name
        self.description = settings.description
        self.execution = settings.execution
        self.dependencies = settings.dependencies
        if logger:
            self.logger = logger
        else:
            self.logger = _logger

    def load(self, instance_settings: BasePluginUserConfig):
        return PluginInstance(instance_settings, self.execution)


class PluginManager:
    plugins: dict[str, PluginDefinition] = {}

    def __init__(self, plugin_dir: str | None = None):
        if not plugin_dir:
            project_root = find_project_root()
            if project_root:
                self.plugin_dir = project_root / "assistants" / "plugins"
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
            raise ValueError(f"Plugin '{plugin_name}' is not registered or failed to load.")
        plugin_definition = self.plugins[plugin_name]
        return plugin_definition.load(instance_settings)
