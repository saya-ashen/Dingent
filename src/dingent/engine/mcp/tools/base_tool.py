from abc import ABC, abstractmethod

from loguru import logger as _logger
from loguru._logger import Logger

from dingent.engine.mcp.core.resource_manager import ResourceManager


class BaseTool(ABC):
    name: str

    def __init__(
        self,
        resource_manager: ResourceManager,
        logger: Logger | None = None,
    ) -> None:
        super().__init__()
        self.resource_manager = resource_manager
        if logger:
            self.logger = logger
        else:
            self.logger = _logger
        assert resource_manager is not None

    @abstractmethod
    async def tool_run(self, *args, **kwargs) -> dict:
        pass
