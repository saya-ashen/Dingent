from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dingent.core.schemas import (
    WorkflowCreate,
    WorkflowEdgeCreate,
    WorkflowEdgeRead,
    WorkflowEdgeUpdate,
    WorkflowNodeCreate,
    WorkflowNodeRead,
    WorkflowNodeUpdate,
    WorkflowRead,
    WorkflowReadBasic,
    WorkflowReplace,
    WorkflowUpdate,
)
from dingent.server.api.dependencies import CurrentWorkspaceAllowGuest, get_workspace_workflow_service
from dingent.server.services.workspace_workflow_service import WorkspaceWorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("", response_model=list[WorkflowReadBasic])
async def list_workflows(
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> list[WorkflowReadBasic]:
    return workspace_workflow_service.list_workflows()


@router.post("", response_model=WorkflowReadBasic, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowReadBasic:
    try:
        wf = workspace_workflow_service.create_workflow(payload)
        return wf
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowRead:
    wf = workspace_workflow_service.get_workflow(workflow_id, eager=True)
    if not wf or not isinstance(wf, WorkflowRead):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return wf


@router.patch("/{workflow_id}", response_model=WorkflowReadBasic)
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowReadBasic:
    try:
        return workspace_workflow_service.update_workflow(workflow_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{workflow_id}", response_model=WorkflowRead)
async def replace_workflow(
    workflow_id: UUID,
    payload: WorkflowReplace,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowRead:
    try:
        workspace_workflow_service.replace_workflow(workflow_id, payload)
        wf = workspace_workflow_service.get_workflow(workflow_id, eager=True)
        if not wf or not isinstance(wf, WorkflowRead):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        return wf

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> None:
    ok = workspace_workflow_service.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return None


# # -----------------------------
# # Lifecycle: start / status / stop
# # -----------------------------
# @router.post("/{workflow_id}/start", response_model=WorkflowRunRead)
# async def start_workflow(
#     workflow_id: UUID,
#     include_self_loops: bool = False,
#     honor_bidirectional: bool = True,
#     reset_existing: bool = True,
#     mutate_assistant_destinations: bool = True,
#     workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
# ) -> WorkflowRunRead:
#     try:
#         run = await workspace_workflow_service.start_workflow(
#             workflow_id,
#             include_self_loops=include_self_loops,
#             honor_bidirectional=honor_bidirectional,
#             reset_existing=reset_existing,
#             mutate_assistant_destinations=mutate_assistant_destinations,
#         )
#         return WorkflowRunRead(workflow_id=run.workflow_id, status=run.status, message=run.message)
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#
#
# @router.get("/{workflow_id}/status", response_model=WorkflowRunRead)
# async def get_workflow_status(
#     workflow_id: UUID,
#     workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
# ) -> WorkflowRunRead:
#     try:
#         run = workspace_workflow_service.get_workflow_status(workflow_id)
#         return WorkflowRunRead(workflow_id=run.workflow_id, status=run.status, message=run.message)
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# @router.post("/{workflow_id}/stop", response_model=WorkflowRunRead)
# async def stop_workflow(
#     workflow_id: UUID,
#     workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
# ) -> WorkflowRunRead:
#     run = await workspace_workflow_service.stop_workflow(workflow_id)
#     return WorkflowRunRead(workflow_id=run.workflow_id, status=run.status, message=run.message)


# -----------------------------
# Nodes Subrouter
# -----------------------------
@router.get("/{workflow_id}/nodes", response_model=list[WorkflowNodeRead])
async def list_nodes(
    workflow_id: UUID,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> list[WorkflowNodeRead]:
    try:
        return workspace_workflow_service.list_nodes(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{workflow_id}/nodes", response_model=WorkflowNodeRead, status_code=status.HTTP_201_CREATED)
async def create_node(
    workflow_id: UUID,
    payload: WorkflowNodeCreate,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowNodeRead:
    try:
        return workspace_workflow_service.create_node(workflow_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{workflow_id}/nodes/{node_id}", response_model=WorkflowNodeRead)
async def update_node(
    workflow_id: UUID,
    node_id: UUID,
    payload: WorkflowNodeUpdate,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowNodeRead:
    try:
        return workspace_workflow_service.update_node(workflow_id, node_id, payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{workflow_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    workflow_id: UUID,
    node_id: UUID,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> None:
    ok = workspace_workflow_service.delete_node(workflow_id, node_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return None


# -----------------------------
# Edges Subrouter
# -----------------------------
@router.get("/{workflow_id}/edges", response_model=list[WorkflowEdgeRead])
async def list_edges(
    workflow_id: UUID,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> list[WorkflowEdgeRead]:
    try:
        return workspace_workflow_service.list_edges(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{workflow_id}/edges", response_model=WorkflowEdgeRead, status_code=status.HTTP_201_CREATED)
async def create_edge(
    workflow_id: UUID,
    payload: WorkflowEdgeCreate,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowEdgeRead:
    try:
        return workspace_workflow_service.create_edge(workflow_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{workflow_id}/edges/{edge_id}", response_model=WorkflowEdgeRead)
async def update_edge(
    workflow_id: UUID,
    edge_id: UUID,
    payload: WorkflowEdgeUpdate,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> WorkflowEdgeRead:
    try:
        return workspace_workflow_service.update_edge(workflow_id, edge_id, payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{workflow_id}/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    workflow_id: UUID,
    edge_id: UUID,
    workspace_workflow_service: WorkspaceWorkflowService = Depends(get_workspace_workflow_service),
) -> None:
    ok = workspace_workflow_service.delete_edge(workflow_id, edge_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    return None
