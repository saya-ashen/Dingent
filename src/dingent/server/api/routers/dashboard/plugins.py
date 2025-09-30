from fastapi import APIRouter, Depends, HTTPException

from dingent.core.db.models import User
from dingent.core.managers.plugin_manager import PluginManager
from dingent.core.schemas import PluginManifest
from dingent.server.api.dependencies import (
    get_current_user,
    get_plugin_manager,
)

router = APIRouter(prefix="/plugins", tags=["Plugins"])


@router.get("", response_model=list[PluginManifest])
async def list_available_plugins(
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    user: User = Depends(get_current_user),
):
    return plugin_manager.list_visible_plugins(user_id=user.id)


# admin only
@router.delete("/{plugin_id}")
async def remove_plugin_global(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    user: User = Depends(get_current_user),
):
    try:
        plugin_manager.delete_plugin(plugin_id=plugin_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    changed = False
    return {"status": "success", "assistants_updated": changed}
