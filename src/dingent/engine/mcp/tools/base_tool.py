from abc import ABC, abstractmethod


class BaseTool(ABC):
    name: str

    @abstractmethod
    async def tool_run(self):
        pass
