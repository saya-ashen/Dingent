from __future__ import annotations

import pickle
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, SQLModel, Session, select, func, delete

from .types import ToolResult  # Assuming ToolResult is defined here

if TYPE_CHECKING:
    from dingent.core.database_manager import DatabaseManager
    from dingent.core.log_manager import LogManager


class Resource(SQLModel, table=True):
    """
    SQLModel representation of a stored resource in the database.
    """

    __tablename__ = "resources"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    data: bytes
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,  # Indexing for faster sorting to find the oldest entry
        nullable=False,
    )


class ResourceManager:
    """
    Uses a shared synchronous SQLite connection via SQLModel to store ToolResult objects.
    """

    def __init__(
        self,
        log_manager: LogManager,
        db_manager: DatabaseManager,
        max_size: int = 100,
    ):
        self._log_manager = log_manager
        self._db_manager = db_manager  # Injected dependency
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("max_size must be a positive integer.")
        self.max_size = max_size

    def initialize(self):
        """
        Ensures the 'resources' table is created via the shared DatabaseManager.
        Call this on startup.
        """
        # The DatabaseManager's init_db handles SQLModel.metadata.create_all()
        self._db_manager.init_db()
        self._log_manager.log_with_context(
            "info",
            "ResourceManager tables ensured via SQLModel.",
            context={"max_size": self.max_size},
        )

    def register(self, resource: ToolResult) -> str:
        """
        Serializes and stores a new resource, enforcing capacity.
        """
        serialized_resource = resource.to_json_bytes()
        new_id = ""

        with self._db_manager.get_session() as session:
            # 1. Enforce max_size by removing the oldest entry if full
            current_size = session.exec(select(func.count(Resource.id))).one()

            if current_size >= self.max_size:
                oldest_resource = session.exec(select(Resource).order_by(Resource.created_at).limit(1)).first()
                if oldest_resource:
                    oldest_id = oldest_resource.id
                    session.delete(oldest_resource)
                    self._log_manager.log_with_context(
                        "warning",
                        "Capacity reached. Removed oldest resource.",
                        context={"removed_resource_id": oldest_id},
                    )

            # 2. Insert the new resource
            new_resource_obj = Resource(data=serialized_resource)
            session.add(new_resource_obj)
            session.commit()
            session.refresh(new_resource_obj)  # Load the generated ID
            new_id = new_resource_obj.id

        # Logging outside the session/transaction
        final_size = len(self)
        self._log_manager.log_with_context(
            "info",
            "ToolResult registered via SQLModel",
            context={
                "resource_id": new_id,
                "total_resources": final_size,
                "capacity_used_percent": round((final_size / self.max_size) * 100, 2),
            },
        )
        return new_id

    def get(self, resource_id: str) -> ToolResult | None:
        """Retrieves and deserializes a resource by its ID."""
        with self._db_manager.get_session() as session:
            # session.get() is the most efficient way to fetch by primary key
            resource_model = session.get(Resource, resource_id)

        if not resource_model:
            self._log_manager.log_with_context("warning", "Resource not found.", context={"resource_id": resource_id})
            return None
        return ToolResult.from_json_bytes(resource_model.data)

    def clear(self) -> None:
        """Deletes all resources."""
        with self._db_manager.get_session() as session:
            statement = delete(Resource)
            session.exec(statement)
            session.commit()
        self._log_manager.log_with_context("info", "All resources cleared.")

    def __len__(self) -> int:
        """Returns the current number of stored resources."""
        with self._db_manager.get_session() as session:
            count = session.exec(select(func.count(Resource.id))).one()
        return count
