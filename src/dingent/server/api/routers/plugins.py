from fastapi import APIRouter, Depends, HTTPException

from dingent.core.config_manager import ConfigManager
from dingent.core.plugin_manager import PluginManager, PluginManifest
from dingent.server.api.dependencies import (
    get_config_manager,
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
    config_manager: ConfigManager = Depends(get_config_manager),
):
    try:
        plugin_manager.remove_plugin(plugin_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    assistants = config_manager.list_assistants()
    changed = False
    for a in assistants:
        new_plugins = [p for p in a.plugins if not (p.plugin_id == plugin_id)]
        if len(new_plugins) != len(a.plugins):
            config_manager.update_plugins_for_assistant(a.id, new_plugins)
            changed = True
    return {"status": "success", "assistants_updated": changed}
