from importlib import resources
from pathlib import Path
from typing import cast

from dingent.core.utils import find_project_root


class CliContext:
    def __init__(self):
        """
        The __init__ method is now empty. All properties are loaded lazily
        when they are first accessed.
        """

    @property
    def project_root(self) -> Path | None:
        """This property now depends on the lazy config_manager."""
        project_root = find_project_root()
        return project_root

    @property
    def backend_port(self) -> int | None:
        """This property now depends on the lazy _config property."""
        return 8000
        return self._config.backend_port

    @property
    def frontend_port(self) -> int | None:
        """This property also depends on the lazy _config property."""
        return 3000
        return self._config.frontend_port

    @property
    def frontend_path(self) -> Path:
        """This property does not depend on app_context and remains unchanged."""
        frontend_dir = resources.files("dingent").joinpath("static")
        return cast(Path, frontend_dir)
