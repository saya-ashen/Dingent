from uuid import UUID

from sqlmodel import Session

from dingent.core.managers.resource_manager import ResourceManager
from dingent.core.schemas import PluginRead
from dingent.core.services.plugin_registry import PluginRegistry
from dingent.core.db.crud import plugin as crud_plugin


class UserPluginService:
    def __init__(
        self,
        user_id: UUID,
        session: Session,
        plugin_registry: PluginRegistry,
        resource_manager: ResourceManager,
    ):
        self.user_id = user_id
        self.session = session
        self.plugin_registry = plugin_registry
        self.resource_manager = resource_manager
        self.middleware = None

    def get_visible_plugins(
        self,
    ) -> list[PluginRead]:
        """
        Gets all manifests from the registry and filters them based on
        the current user's permissions.
        (Permission logic is a placeholder for now.)
        """
        visible_plugins = crud_plugin.get_all_plugins(self.session)
        plugin_reads = [PluginRead.model_validate(plugin) for plugin in visible_plugins]
        return plugin_reads
