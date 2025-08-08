from pathlib import Path

import toml


from dingent.engine.plugins.manager import PluginManager
from dingent.utils import find_project_root


class CliContext:
    def __init__(self):
        self.project_root: Path | None = find_project_root()
        self.config: dict = {}

        if self.project_root:
            config_path = self.project_root / "dingent.toml"
            self.config = toml.load(config_path)

    @property
    def is_in_project(self) -> bool:
        return self.project_root is not None

    @property
    def assistants_path(self) -> Path | None:
        if not self.is_in_project:
            return None
        # 从配置中读取路径，提供默认值
        assistants_dir = self.config.get("components", {}).get("assistants", "assistants")
        return self.project_root / assistants_dir

    @property
    def backend_path(self) -> Path | None:
        if not self.is_in_project:
            return None
        # 从配置中读取路径，提供默认值
        backend_dir = self.config.get("components", {}).get("backend", "backend")
        return self.project_root / backend_dir

    @property
    def frontend_path(self) -> Path | None:
        if not self.is_in_project:
            return None
        # 从配置中读取路径，提供默认值
        frontend_dir = self.config.get("components", {}).get("frontend", "frontend")
        return self.project_root / frontend_dir

    @property
    def assistants_plugin_path(self) -> Path | None:
        if not self.assistants_path:
            return None
        plugin_dir = self.config.get("plugins", {}).get("directory", "plugins")
        return self.assistants_path / plugin_dir

    @property
    def assistants_plugin_manager(self) -> PluginManager | None:
        if not self.assistants_plugin_path:
            return None
        return PluginManager(plugin_dir=self.assistants_plugin_path)
