from __future__ import annotations

from pathlib import Path

from dingent.core.config import settings
from dingent.core.managers.user_secret_manager import UserSecretManager
from dingent.core.paths import paths


class AppContext:
    """A container for all manager instances to handle dependency injection."""

    def __init__(self, project_root: Path | None = None):
        self.secret_manager = UserSecretManager(master_password=settings.DINGENT_MASTER_KEY.get_secret_value())
        self.plugins_dir = paths.plugins_dir

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
