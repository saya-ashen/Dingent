from abc import ABC, abstractmethod

from loguru import logger as _logger
from loguru._logger import Logger

from .resource_manager import ResourceManager
from .types import ToolBaseSettings


class BaseTool(ABC):
    name: str
    description: str
    exclude_args: list[str] = []

    def __init__(
        self,
        config: ToolBaseSettings,
        resource_manager: ResourceManager,
        logger: Logger | None = None,
        **kwargs,
    ) -> None:
        super().__init__()
        self.resource_manager = resource_manager
        self.name = config.name
        self.description = config.description
        if logger:
            self.logger = logger
        else:
            self.logger = _logger
        assert resource_manager is not None

    @abstractmethod
    async def tool_run(self, *args, **kwargs) -> dict:
        pass
