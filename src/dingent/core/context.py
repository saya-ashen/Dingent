# In dingent/core/context.py
from __future__ import annotations

from pathlib import Path

from dingent.core.market_service import MarketService
from dingent.engine.graph_manager import GraphManager

from .analytics_manager import AnalyticsManager
from .assistant_manager import AssistantManager
from .config_manager import ConfigManager
from .llm_manager import LLMManager
from .log_manager import LogManager
from .plugin_manager import PluginManager
from .resource_manager import ResourceManager
from .utils import find_project_root
from .workflow_manager import WorkflowManager


class AppContext:
    """A container for all manager instances to handle dependency injection."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or find_project_root()
        if not self.project_root:
            return
        # Initialize in order of dependency (least dependent first)
        self.log_manager = LogManager()
        self.config_manager = ConfigManager(self.project_root, self.log_manager)
        self.resource_manager = ResourceManager(self.log_manager, self.project_root / ".dingent" / "data" / "resources.db")
        self.llm_manager = LLMManager(self.log_manager)

        self.analytics_manager = AnalyticsManager("test_project")
        self.analytics_manager.register()

        plugin_dir = self.project_root / "plugins"
        self.plugin_manager = PluginManager(plugin_dir, self.resource_manager, self.log_manager)

        self.assistant_manager = AssistantManager(self.config_manager, self.plugin_manager, self.log_manager)

        self.workflow_manager = WorkflowManager(
            self.config_manager,
            self.log_manager,
            self.assistant_manager,
        )
        self.market_service = MarketService(self.config_manager.project_root, self.log_manager)
        self.graph_manager = GraphManager(self)

    async def close(self):
        """Close all managers that require cleanup."""
        self.resource_manager.close()
        await self.assistant_manager.aclose()


_app_context_instance: AppContext | None = None


def initialize_app_context() -> AppContext:
    """
    创建并返回AppContext的单例。此函数应仅在应用启动时（lifespan中）调用一次。
    """
    global _app_context_instance
    if _app_context_instance is None:
        _app_context_instance = AppContext()
    return _app_context_instance


def get_app_context() -> AppContext:
    """
    获取已初始化的AppContext单例。
    如果在应用启动完成前调用，将引发错误。
    这是在非注入场景下安全获取context的方法。
    """
    global _app_context_instance
    if _app_context_instance is None:
        # 防止在应用还未准备好时就尝试访问context
        raise RuntimeError("AppContext has not been initialized. It should be initialized by the application's lifespan manager at startup.")
    return _app_context_instance
