from fastapi import APIRouter, Depends, HTTPException

from dingent.core.types import Workflow, WorkflowCreate, WorkflowUpdate
from dingent.core.workflow_manager import WorkflowManager
from dingent.server.api.dependencies import (
    get_workflow_manager,
)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("", response_model=list[Workflow])
async def list_workflows(
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    return workflow_manager.list_workflows()


@router.post("", response_model=Workflow)
async def create_workflow(
    wf_create: WorkflowCreate,
    make_active: bool = False,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    try:
        wf = workflow_manager.create_workflow(wf_create, make_active=make_active)
        return wf
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active")
async def get_active_workflow(
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    return {"current_workflow": workflow_manager.active_workflow_id}


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(
    workflow_id: str,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    wf = workflow_manager.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}", response_model=Workflow)
async def replace_workflow(
    workflow_id: str,
    workflow: Workflow,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    if workflow.id != workflow_id:
        raise HTTPException(status_code=400, detail="Workflow ID mismatch")
    try:
        return workflow_manager.save_workflow(workflow)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{workflow_id}", response_model=Workflow)
async def patch_workflow(
    workflow_id: str,
    patch: WorkflowUpdate,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    try:
        return workflow_manager.update_workflow(workflow_id, patch)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    ok = workflow_manager.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "message": f"Workflow {workflow_id} deleted"}


@router.post("/{workflow_id}/activate")
async def activate_workflow(
    workflow_id: str,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    try:
        workflow_manager.set_active(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "success", "current_workflow": workflow_id}


@router.post("/{workflow_id}/instantiate")
async def instantiate_workflow(
    workflow_id: str,
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """
    根据 workflow 构建（或重用）assistant 实例并设置 destinations。
    仅在需要手动触发时使用；否则可在激活时自动调用。
    """
    try:
        # 这里调用 workflow_manager.instantiate_workflow_assistants (若保留该方法)。
        if not hasattr(workflow_manager, "instantiate_workflow_assistants"):
            raise HTTPException(status_code=400, detail="Runtime instantiation not supported in current build.")
        result = await workflow_manager.instantiate_workflow_assistants(workflow_id)
        return {
            "status": "success",
            "assistants": {name: {"destinations": inst.destinations} for name, inst in result.items()},
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
