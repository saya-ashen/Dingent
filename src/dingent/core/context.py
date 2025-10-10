# In dingent/core/context.py
from __future__ import annotations

from pathlib import Path


from .utils import find_project_root


UNIFIED_DB_PATH = ".dingent/data/dingent.sqlite"


class AppContext:
    """A container for all manager instances to handle dependency injection."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or find_project_root()
        if not self.project_root:
            return
        # Initialize in order of dependency (least dependent first)

        plugin_dir = self.project_root / "plugins"

        # self.market_service = MarketService(self.config_manager.project_root, self.log_manager)

    async def close_async_components(self):
        """
        Gracefully close all managers that require async cleanup.
        """


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
