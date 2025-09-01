from functools import cached_property
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, cast

from dingent.core.config_manager import ConfigManager
from dingent.core.log_manager import LogManager
from dingent.core.utils import find_project_root

if TYPE_CHECKING:
    from dingent.core.settings import AppSettings


class CliContext:
    def __init__(self):
        """
        The __init__ method is now empty. All properties are loaded lazily
        when they are first accessed.
        """

    @cached_property
    def config_manager(self) -> "ConfigManager":
        """Lazily gets the config_manager from the app_context."""
        log_manager = LogManager()
        config_manager = ConfigManager(self.project_root, log_manager)
        return config_manager

    @cached_property
    def _config(self) -> "AppSettings":
        """Lazily gets the settings from the config_manager."""
        return self.config_manager.get_settings()

    @property
    def project_root(self) -> Path | None:
        """This property now depends on the lazy config_manager."""
        project_root = find_project_root()
        return project_root

    @property
    def backend_port(self) -> int | None:
        """This property now depends on the lazy _config property."""
        return self._config.backend_port

    @property
    def frontend_port(self) -> int | None:
        """This property also depends on the lazy _config property."""
        return self._config.frontend_port

    @property
    def frontend_path(self) -> Path:
        """This property does not depend on app_context and remains unchanged."""
        frontend_dir = resources.files("dingent").joinpath("static", "frontend")
        return cast(Path, frontend_dir)
