from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, asc, delete, func, select

from dingent.core.db.crud import resource as crud_resource
from dingent.core.db.models import Resource
from dingent.core.managers.log_manager import LogManager
from dingent.core.schemas import ResourceCreate


def get_oldest_resource_for_user(session: Session, user_id: UUID) -> Resource | None:
    """Helper function to get the oldest resource for a specific user."""
    statement = select(Resource).where(Resource.user_id == user_id).order_by(asc(Resource.created_at)).limit(1)
    result = session.exec(statement).first()
    return result


class ResourceManager:
    """
    Manages the persistence of Resource objects in the database in a multi-tenant fashion.
    """

    def __init__(
        self,
        log_manager: LogManager,
        max_size: int = 1000,
    ):
        """
        Initializes the ResourceManager.

        Args:
            log_manager: The logger instance.
            max_size: The maximum number of resources to store per user.
        """
        self._log_manager = log_manager
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("max_size must be a positive integer.")
        self.max_size = max_size

    def create_resource(self, user_id: UUID, resource: ResourceCreate, session: Session) -> Resource:
        """
        Saves a new Resource object to the database, enforcing per-user capacity.
        The incoming 'resource' object must have the user_id populated.

        Args:
            resource: The Resource object to save.
            session: The database session.

        Returns:
            The saved Resource object.
        """
        # Check current size for the specific user
        statement = select(func.count()).where(Resource.user_id == user_id)
        current_size = session.exec(statement).one()

        if current_size >= self.max_size:
            oldest_resource = get_oldest_resource_for_user(session, user_id)
            if oldest_resource:
                self._log_manager.log_with_context(
                    "warning",
                    "Resource capacity reached for user. Removing oldest resource.",
                    context={
                        "user_id": user_id,
                        "removed_resource_id": oldest_resource.id,
                    },
                )
                session.delete(oldest_resource)
                session.commit()  # Commit deletion before adding the new one

        resource_db = crud_resource.create_resource(user_id=user_id, payload=resource, session=session)

        self._log_manager.log_with_context(
            "info",
            "Resource registered in DB",
            context={"resource_id": resource_db.id, "user_id": resource_db.user_id},
        )
        return resource_db

    def get_resource(self, resource_id: UUID, user_id: UUID, session: Session) -> Resource | None:
        """
        Retrieves a resource by its ID, ensuring it belongs to the specified user.

        Args:
            resource_id: The UUID of the resource to retrieve.
            user_id: The UUID of the user who owns the resource.
            session: The database session.

        Returns:
            The Resource object if found and owned by the user, otherwise None.
        """
        statement = select(Resource).where(Resource.id == resource_id, Resource.user_id == user_id)
        resource = session.exec(statement).first()

        if not resource:
            self._log_manager.log_with_context(
                "warning",
                "Resource not found in DB or access denied.",
                context={"resource_id": resource_id, "user_id": user_id},
            )
        return resource

    def list_resources_by_user(self, user_id: UUID, session: Session):
        """
        Lists all resources for a specific user.

        Args:
            user_id: The UUID of the user.
            session: The database session.

        Returns:
            A list of Resource objects.
        """
        statement = select(Resource).where(Resource.user_id == user_id)
        return session.exec(statement).all()

    def delete_all_by_user(self, user_id: UUID, session: Session) -> None:
        """
        Deletes all resources for a specific user from the database.

        Args:
            user_id: The UUID of the user whose resources should be cleared.
            session: The database session.
        """
        statement = delete(Resource).where(Resource.user_id == user_id)  # type: ignore
        session.exec(statement)
        session.commit()
        self._log_manager.log_with_context(
            "info",
            "All resources cleared from DB for user.",
            context={"user_id": user_id},
        )
