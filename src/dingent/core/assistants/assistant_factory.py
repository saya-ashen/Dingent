from __future__ import annotations

from .assistant import AssistantRuntime
from .schemas import AssistantSpec


class AssistantFactory:
    """
    一个无状态的工厂，负责根据 Assistant 配置创建运行时实例。
    这个类的实例可以在整个应用的生命周期中共享（单例）。
    """

    def __init__(self, plugin_manager, log_manager):
        self._plugin_manager = plugin_manager
        self._log_manager = log_manager

    async def create_runtime(self, assistant_config: AssistantSpec) -> AssistantRuntime:
        """
        根据给定的助手配置，创建一个运行时实例。
        这是一个纯粹的构建过程，与用户或请求无关。
        """
        return await AssistantRuntime.create_runtime(
            plugin_manager=self._plugin_manager,
            assistant=assistant_config,
            log_method=self._log_manager.log_with_context,
        )
