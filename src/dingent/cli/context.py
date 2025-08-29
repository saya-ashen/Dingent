from functools import cached_property
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dingent.core.assistant_manager import AssistantManager
    from dingent.core.config_manager import ConfigManager
    from dingent.core.context import AppContext
    from dingent.core.plugin_manager import PluginManager
    from dingent.core.settings import AppSettings


class CliContext:
    def __init__(self):
        """
        The __init__ method is now empty. All properties are loaded lazily
        when they are first accessed.
        """
        pass

    @cached_property
    def app_context(self) -> "AppContext":
        """
        This property creates and caches the app_context.
        It will only be executed once, the first time it's called.
        """
        from dingent.core import get_app_context

        return get_app_context()

    @cached_property
    def config_manager(self) -> "ConfigManager":
        """Lazily gets the config_manager from the app_context."""
        return self.app_context.config_manager

    @cached_property
    def plugin_manager(self) -> "PluginManager":
        """Lazily gets the plugin_manager from the app_context."""
        return self.app_context.plugin_manager

    @cached_property
    def assistant_manager(self) -> "AssistantManager":
        """Lazily gets the assistant_manager from the app_context."""
        return self.app_context.assistant_manager

    @cached_property
    def _config(self) -> "AppSettings":
        """Lazily gets the settings from the config_manager."""
        return self.config_manager.get_settings()

    @property
    def project_root(self) -> Path:
        """This property now depends on the lazy config_manager."""
        return self.app_context.project_root

    @property
    def frontend_path(self) -> Path:
        """This property does not depend on app_context and remains unchanged."""
        frontend_dir = resources.files("dingent").joinpath("static", "frontend")
        return frontend_dir

    @property
    def backend_port(self) -> int | None:
        """This property now depends on the lazy _config property."""
        return self._config.backend_port

    @property
    def frontend_port(self) -> int | None:
        """This property also depends on the lazy _config property."""
        return self._config.frontend_port
