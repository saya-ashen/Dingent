# In dingent/core/context.py
from __future__ import annotations

from pathlib import Path

from .assistant_manager import AssistantManager
from .config_manager import ConfigManager
from .llm_manager import LLMManager
from .plugin_manager import PluginManager
from .resource_manager import ResourceManager
from .utils import find_project_root
from .workflow_manager import WorkflowManager


class AppContext:
    """A container for all manager instances to handle dependency injection."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or find_project_root()
        if not self.project_root:
            raise RuntimeError("Could not find project root (dingent.toml).")

        # Initialize in order of dependency (least dependent first)
        self.config_manager = ConfigManager(self.project_root)
        self.resource_manager = ResourceManager(self.project_root / ".dingent" / "data" / "resources.db")
        self.llm_manager = LLMManager()

        self.plugin_manager = PluginManager(self.config_manager, self.resource_manager)

        self.assistant_manager = AssistantManager(self.config_manager, self.plugin_manager)

        self.workflow_manager = WorkflowManager(
            self.config_manager,
            self.assistant_manager,
        )

    async def close(self):
        """Close all managers that require cleanup."""
        self.resource_manager.close()
        await self.assistant_manager.aclose()


# Optional: You can create a global context if you want to access it easily,
# but it's better to create it once in your app's entry point.
_app_context: AppContext | None = None


def get_app_context() -> AppContext:
    global _app_context
    if _app_context is None:
        _app_context = AppContext()
    return _app_context
