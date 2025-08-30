from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from dingent.core.config_manager import ConfigManager
from dingent.core.workflow_manager import WorkflowManager
from dingent.server.api.dependencies import (
    get_config_manager,
    get_workflow_manager,
)
from dingent.server.api.schemas import AppAdminDetail

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=AppAdminDetail)
async def get_app_settings(
    config_manager: ConfigManager = Depends(get_config_manager),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    settings = config_manager.get_settings()
    workflows_summary = [{"id": wf.id, "name": wf.name} for wf in workflow_manager.list_workflows()]
    data = {
        "llm": settings.llm.model_dump(mode="json") if settings.llm else {},
        "current_workflow": workflow_manager.active_workflow_id,
        "workflows": workflows_summary,
    }
    return AppAdminDetail(**data)


@router.patch("")
async def update_app_settings(
    payload: dict,
    config_manager: ConfigManager = Depends(get_config_manager),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """
    部分更新全局配置 (llm / current_workflow)。
    """
    patch: dict[str, Any] = {}
    if "llm" in payload:
        patch["llm"] = payload["llm"]
    if "current_workflow" in payload:
        cw = payload["current_workflow"]
        patch["current_workflow"] = cw
        if cw:
            try:
                workflow_manager.set_active(cw)
            except Exception:
                pass
        else:
            workflow_manager.clear_active()
    if not patch:
        return {"status": "noop", "message": "No updatable keys provided."}
    try:
        config_manager.update_global(patch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {e}")
    return {"status": "ok"}
