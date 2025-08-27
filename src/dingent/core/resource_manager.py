import uuid
from collections import OrderedDict

from loguru import logger

from .log_manager import log_with_context
from .types import ToolResult


class ResourceManager:
    """
    存储 ToolResult（工具完整输出）的简单内存资源管理器（FIFO）。
    只在会话里携带 ID，前端用 ID 回取完整内容。
    """

    def __init__(self, max_size: int = 100):
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("max_size must be a positive integer.")
        self.max_size = max_size
        self._resources: OrderedDict[str, ToolResult] = OrderedDict()
        logger.info(f"ResourceManager initialized with a maximum capacity of {self.max_size} resources.")

    def register(self, resource: ToolResult) -> str:
        if len(self._resources) >= self.max_size:
            oldest_id, _ = self._resources.popitem(last=False)
            logger.warning(f"Capacity reached. Removing oldest resource with ID: {oldest_id}")

        new_id = str(uuid.uuid4())
        self._resources[new_id] = resource

        log_with_context(
            "info",
            "ToolResult registered",
            context={
                "resource_id": new_id,
                "payload_count": len(resource.display),
                "has_data": resource.data is not None,
                "total_resources": len(self._resources),
                "capacity_used_percent": round((len(self._resources) / self.max_size) * 100, 2),
            },
            correlation_id=f"toolres_{new_id[:8]}",
        )
        return new_id

    def get(self, resource_id: str):
        resource = self._resources.get(resource_id)
        if not resource:
            return None
        return resource

    def get_model_text(self, resource_id: str) -> str | None:
        r = self._resources.get(resource_id)
        return r.model_text if r else None

    def clear(self) -> None:
        self._resources.clear()
        logger.info("All resources have been cleared from the manager.")

    def __len__(self) -> int:
        return len(self._resources)

    def __repr__(self) -> str:
        return f"<ResourceManager(current_size={len(self)}, max_size={self.max_size})>"


resource_manager = None


def get_resource_manager() -> ResourceManager:
    global resource_manager
    if resource_manager is None:
        resource_manager = ResourceManager(max_size=100)
        logger.info("Created a new ResourceManager instance.")
    return resource_manager
