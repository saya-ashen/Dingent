from typing import Any

from fastapi import APIRouter, HTTPException

from dingent.server.api.schemas import AppAdminDetail

router = APIRouter(prefix="/settings", tags=["Settings"])


# Admin only
@router.get("", response_model=AppAdminDetail)
async def get_app_settings():
    pass


@router.patch("")
async def update_app_settings(
    payload: dict,
    # workflow_manager: WorkflowManager = Depends(get_workflow_manager),
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
