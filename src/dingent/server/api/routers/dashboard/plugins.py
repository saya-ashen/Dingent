from fastapi import APIRouter, Depends, HTTPException

from dingent.core.managers.plugin_manager import PluginManager
from dingent.core.schemas import PluginManifest
from dingent.server.api.dependencies import (
    get_plugin_manager,
)

router = APIRouter(prefix="/plugins", tags=["Plugins"])


@router.get("", response_model=list[PluginManifest])
async def list_available_plugins(
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    return list(plugin_manager.list_plugins().values())


@router.delete("/{plugin_id}")
async def remove_plugin_global(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    try:
        plugin_manager.remove_plugin(plugin_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    changed = False
    return {"status": "success", "assistants_updated": changed}
