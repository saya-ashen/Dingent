from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from dingent.core.db.models import User, Workspace
from dingent.core.schemas import AssistantCreate, AssistantRead, AssistantUpdate, PluginAddToAssistant, PluginUpdateOnAssistant
from dingent.server.api.dependencies import (
    get_current_user,
    get_current_workspace,
    get_workspace_assistant_service,
)
from dingent.server.services.workspace_assistant_service import WorkspaceAssistantService

router = APIRouter(prefix="/assistants", tags=["Assistants"])


@router.get("", response_model=list[AssistantRead])
async def list_assistants(
    current_workspace: Workspace = Depends(get_current_workspace),
    workspace_assistant_service: WorkspaceAssistantService = Depends(get_workspace_assistant_service),
) -> list[AssistantRead]:
    assistant_reads = await workspace_assistant_service.get_all_assistant_details(workspace_id=current_workspace.id)
    return assistant_reads


@router.post("", response_model=AssistantRead)
async def create_assistant(
    assistant_create: AssistantCreate,
    current_workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_user),
    workspace_assistant_service: WorkspaceAssistantService = Depends(get_workspace_assistant_service),
) -> AssistantRead:
    new_assistant = await workspace_assistant_service.create_assistant(
        assistant_create,
        workspace_id=current_workspace.id,
        user_id=current_user.id,
    )
    return new_assistant


@router.patch("/{assistant_id}", response_model=AssistantRead)
async def update_assistant(
    *,
    assistant_id: UUID,
    assistant_update: AssistantUpdate,
    workspace_assistant_service: WorkspaceAssistantService = Depends(get_workspace_assistant_service),
    _current_workspace: Workspace = Depends(get_current_workspace),  # For permission check
):
    updated_assistant = await workspace_assistant_service.update_assistant(assistant_id, assistant_update)
    return updated_assistant


@router.delete("/{assistant_id}")
async def delete_assistant(
    *,
    assistant_id: UUID,
    workspace_assistant_service: WorkspaceAssistantService = Depends(get_workspace_assistant_service),
):
    await workspace_assistant_service.delete_assistant(assistant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{assistant_id}/plugins", response_model=AssistantRead)
async def add_plugin_to_assistant(
    *,
    assistant_id: UUID,
    plugin_add: PluginAddToAssistant,
    workspace_assistant_service: WorkspaceAssistantService = Depends(get_workspace_assistant_service),
):
    updated_assistant = await workspace_assistant_service.add_plugin_to_assistant(assistant_id, plugin_add.registry_id)
    return updated_assistant


@router.patch("/{assistant_id}/plugins/{plugin_id}", response_model=AssistantRead)
async def update_plugin_on_assistant(
    *,
    assistant_id: UUID,
    plugin_id: UUID,
    plugin_update: PluginUpdateOnAssistant,
    workspace_assistant_service: WorkspaceAssistantService = Depends(get_workspace_assistant_service),
):
    """
    Updates a plugin's configuration for a specific assistant (e.g., enables/disables it).
    """
    updated_assistant = await workspace_assistant_service.update_plugin_on_assistant(
        assistant_id,
        plugin_id,
        plugin_update,
    )
    return updated_assistant


@router.delete("/{assistant_id}/plugins/{registry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_plugin_from_assistant(
    *,
    assistant_id: UUID,
    registry_id: str,
    workspace_assistant_service: WorkspaceAssistantService = Depends(get_workspace_assistant_service),
):
    """
    Removes the association between a plugin and an assistant.
    """
    await workspace_assistant_service.remove_plugin_from_assistant(assistant_id, registry_id)
    return
