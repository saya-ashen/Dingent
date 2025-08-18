from functools import cached_property
from pathlib import Path

import toml

from dingent.core import get_assistant_manager
from dingent.core.plugin_manager import get_plugin_manager
from dingent.core.utils import find_project_root


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
    def backend_config(self):
        return self.config.get("backend", {})

    @property
    def frontend_config(self):
        return self.config.get("frontend", {})

    @property
    def backend_path(self) -> Path | None:
        if not self.is_in_project:
            return None

        backend_dir = self.backend_config.get("directory", "backend")
        return self.project_root / backend_dir

    @property
    def frontend_path(self) -> Path | None:
        if not self.is_in_project:
            return None
        # 从配置中读取路径，提供默认值
        frontend_dir = self.frontend_config.get("directory", "frontend")
        return self.project_root / frontend_dir

    @property
    def plugin_path(self) -> Path | None:
        if not self.backend_path:
            return None
        plugin_dir = self.backend_config.get("plugins", {}).get("directory", "plugins")
        return self.backend_path / plugin_dir

    @cached_property
    def plugin_manager(self):
        if not self.plugin_path:
            return None
        return get_plugin_manager()

    @cached_property
    def assistant_manager(self):
        if not self.plugin_manager:
            return None
        return get_assistant_manager()

    @property
    def backend_port(self) -> int | None:
        """Reads the backend port from the config, with a default of 8000."""
        if not self.is_in_project:
            return None
        return self.config.get("components", {}).get("backend", {}).get("port", 8000)

    @property
    def frontend_port(self) -> int | None:
        """Reads the frontend port from the config, with a default of 3000."""
        if not self.is_in_project:
            return None
        return self.config.get("components", {}).get("frontend", {}).get("port", 3000)

    @property
    def dashboard_port(self) -> int | None:
        """Reads the admin dashboard port from the config, with a default of 8501."""
        if not self.is_in_project:
            return None
        return self.config.get("components", {}).get("admin_dashboard", {}).get("port", 8501)
