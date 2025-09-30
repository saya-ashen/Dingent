from uuid import UUID
from sqlmodel import Session, select

from dingent.core.db.models import Plugin


def get_plugin_by_id(*, db: Session, id: UUID) -> Plugin | None:
    """Gets a plugin by its UUID."""
    return db.get(Plugin, id)


def get_plugin_by_slug(db: Session, plugin_slug: str) -> Plugin | None:
    """Gets a plugin by its unique plugin_slug."""
    return db.exec(select(Plugin).where(Plugin.plugin_slug == plugin_slug)).first()


def get_all_plugins(db: Session):
    """Gets all plugins from the database."""
    statement = select(Plugin)
    results = db.exec(statement).all()
    return results


# --- Update Operation ---


# --- Delete Operation ---


def remove_plugin(db: Session, *, id: UUID) -> Plugin | None:
    """
    Deletes a plugin from the database by its ID.

    Args:
        db: The database session.
        id: The UUID of the plugin to delete.

    Returns:
        The deleted Plugin object, or None if it was not found.
    """
    plugin_to_delete = db.get(Plugin, id)

    if not plugin_to_delete:
        return None

    db.delete(plugin_to_delete)
    db.commit()

    return plugin_to_delete
