from functools import cached_property
from importlib import resources


class CliContext:
    def __init__(self):
        from dingent.core import get_app_context

        app_context = get_app_context()

        config_manager = app_context.config_manager

        self._config = config_manager.get_settings()
        self._project_root = config_manager.project_root

    @cached_property
    def plugin_manager(self):
        from dingent.core import get_app_context

        app_context = get_app_context()

        return app_context.plugin_manager

    @cached_property
    def assistant_manager(self):
        from dingent.core import get_app_context

        app_context = get_app_context()

        return app_context.assistant_manager

    @property
    def project_root(self):
        return self._project_root

    @property
    def frontend_path(self):
        frontend_dir = resources.files("dingent").joinpath("static", "frontend")
        return frontend_dir

    @property
    def backend_port(self) -> int | None:
        return self._config.backend_port

    @property
    def frontend_port(self) -> int | None:
        return self._config.frontend_port
