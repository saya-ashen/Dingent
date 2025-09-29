from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Session, asc, select, func, delete

from dingent.core.db.models import Resource


if TYPE_CHECKING:
    from dingent.managers.core.log_manager import LogManager


def get_oldest_record(session: Session, model):
    statement = select(model).order_by(asc(model.created_at)).limit(1)
    result = session.exec(statement).first()
    return result


class ResourceManager:
    """
    Manages the persistence of Resource objects in the database.
    It handles its own database sessions via a provided session factory.
    """

    def __init__(
        self,
        log_manager: LogManager,
        max_size: int = 1000,
    ):
        """
        Initializes the ResourceManager.

        Args:
            db_session_factory: A function that provides a database session context manager.
            log_manager: The logger instance.
            max_size: The maximum number of resources to store.
        """
        self._log_manager = log_manager
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("max_size must be a positive integer.")
        self.max_size = max_size

    def create(self, resource: Resource, session: Session) -> Resource:
        """
        Saves a new Resource object to the database, enforcing capacity.
        The incoming 'resource' object is expected to be fully populated by the business logic layer.

        Args:
            resource: The Resource object to save.

        Returns:
            The saved Resource object, now with its database-generated ID.
        """
        statement = select(func.count()).select_from(Resource)
        current_size = session.exec(statement).one()

        if current_size >= self.max_size:
            oldest_resource = get_oldest_record(session, Resource)
            if oldest_resource:
                self._log_manager.log_with_context(
                    "warning",
                    "Resource capacity reached. Removing oldest resource.",
                    context={"removed_resource_id": oldest_resource.id},
                )
                session.delete(oldest_resource)
                session.commit()  # Commit the deletion before adding the new one

        session.add(resource)
        session.commit()
        session.refresh(resource)  # Load the generated ID and other defaults

        self._log_manager.log_with_context(
            "info",
            "Resource registered in DB",
            context={"resource_id": resource.id, "user_id": resource.user_id},
        )
        return resource

    def get_by_id(self, resource_id: UUID, session: Session) -> Resource | None:
        """
        Retrieves a resource by its ID.

        Args:
            resource_id: The UUID of the resource to retrieve.

        Returns:
            The Resource object if found, otherwise None.
        """
        resource = session.get(Resource, resource_id)
        if not resource:
            self._log_manager.log_with_context("warning", "Resource not found in DB.", context={"resource_id": resource_id})
        return resource

    def clear(self, session: Session) -> None:
        """Deletes all resources from the database."""
        session.exec(delete(Resource))
        session.commit()
        self._log_manager.log_with_context("info", "All resources cleared from DB.")
