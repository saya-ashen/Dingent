import uuid
from collections import OrderedDict

from loguru import logger

from ..tools.types import ToolOutput


class ResourceManager:
    """
    Manages the storage and retrieval of resources with a fixed capacity.

    This manager stores resources in memory. When a new resource is registered,
    it is assigned a unique ID. If the manager is at full capacity, the oldest
    resource is automatically removed to make space for the new one (FIFO - First-In, First-Out).
    """

    def __init__(self, max_size: int = 100):
        """
        Initializes the ResourceManager.

        Args:
            max_size (int): The maximum number of resources that can be stored.
                            If this limit is exceeded, the oldest resource will be discarded.
                            Must be a positive integer.
        """
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("max_size must be a positive integer.")

        self.max_size = max_size
        # An OrderedDict remembers the order in which items were inserted.
        # This is perfect for easily finding and removing the oldest item.
        self._resources: OrderedDict[str, ToolOutput] = OrderedDict()
        logger.info(f"ResourceManager initialized with a maximum capacity of {self.max_size} resources.")

    def register(self, resource: ToolOutput) -> str:
        """
        Stores a resource in the manager and returns a unique ID for it.

        If the manager is already full, it will remove the oldest resource
        before adding the new one.

        Args:
            resource (Any): The resource object to be stored. It can be of any type.

        Returns:
            str: A unique string ID that can be used to retrieve the resource later.
        """
        # Check if the manager is full
        if len(self._resources) >= self.max_size:
            # popitem(last=False) removes the first item that was inserted (the oldest).
            oldest_id, oldest_resource = self._resources.popitem(last=False)
            logger.warning(f"Capacity reached. Removing oldest resource with ID: {oldest_id}")

        # Generate a new unique ID
        new_id = str(uuid.uuid4())

        # Store the new resource
        self._resources[new_id] = resource
        logger.info(f"Resource registered successfully with ID: {new_id}")

        return new_id

    def get(self, resource_id: str) -> ToolOutput:
        """
        Retrieves a resource using its unique ID.

        Args:
            resource_id (str): The unique ID of the resource to retrieve.

        Returns:
            Any: The stored resource object.

        Raises:
            KeyError: If no resource with the given ID is found.
        """
        if resource_id not in self._resources:
            raise KeyError(f"No resource found with ID '{resource_id}'. It might have been evicted or never existed.")

        return self._resources[resource_id]

    def clear(self) -> None:
        """
        Removes all resources from the manager.
        """
        self._resources.clear()
        logger.info("All resources have been cleared from the manager.")

    def __len__(self) -> int:
        """Returns the current number of stored resources."""
        return len(self._resources)

    def __repr__(self) -> str:
        """Provides a developer-friendly representation of the manager."""
        return f"<ResourceManager(current_size={len(self)}, max_size={self.max_size})>"
