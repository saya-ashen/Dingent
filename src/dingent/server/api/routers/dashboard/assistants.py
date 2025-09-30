from uuid import UUID

from fastapi import APIRouter, Depends, status, Response

from dingent.core.schemas import AssistantCreate, AssistantRead, AssistantUpdate, PluginAddToAssistant, PluginUpdateOnAssistant
from dingent.server.api.dependencies import (
    get_user_assistant_service,
)
from dingent.server.services.user_assistant_service import UserAssistantService

router = APIRouter(prefix="/assistants", tags=["Assistants"])


@router.get("", response_model=list[AssistantRead])
async def list_assistants(
    user_assistant_service: UserAssistantService = Depends(get_user_assistant_service),
) -> list[AssistantRead]:
    assistant_reads = await user_assistant_service.get_all_assistant_details()
    return assistant_reads


@router.post("", response_model=AssistantRead)
async def create_assistant(
    assistant_create: AssistantCreate,
    user_assistant_service: UserAssistantService = Depends(get_user_assistant_service),
) -> AssistantRead:
    new_assistant = await user_assistant_service.create_assistant(assistant_create)
    return new_assistant


@router.patch("/{assistant_id}", response_model=AssistantRead)
async def update_assistant(
    *,
    assistant_id: UUID,
    assistant_update: AssistantUpdate,
    user_assistant_service: UserAssistantService = Depends(get_user_assistant_service),
):
    updated_assistant = await user_assistant_service.update_assistant(assistant_id, assistant_update)
    return updated_assistant


@router.delete("/{assistant_id}")
async def delete_assistant(
    *,
    assistant_id: UUID,
    user_assistant_service: UserAssistantService = Depends(get_user_assistant_service),
):
    await user_assistant_service.delete_assistant(assistant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{assistant_id}/plugins", response_model=AssistantRead)
async def add_plugin_to_assistant(
    *,
    assistant_id: UUID,
    plugin_add: PluginAddToAssistant,
    user_assistant_service: UserAssistantService = Depends(get_user_assistant_service),
):
    updated_assistant = await user_assistant_service.add_plugin_to_assistant(assistant_id, plugin_add.id)
    return updated_assistant


@router.patch("/{assistant_id}/plugins/{plugin_id}", response_model=AssistantRead)
async def update_plugin_on_assistant(
    *,
    assistant_id: UUID,
    plugin_id: UUID,
    plugin_update: PluginUpdateOnAssistant,
    user_assistant_service: UserAssistantService = Depends(get_user_assistant_service),
):
    """
    Updates a plugin's configuration for a specific assistant (e.g., enables/disables it).
    """
    updated_assistant = await user_assistant_service.update_plugin_on_assistant(assistant_id, plugin_id, plugin_update)
    return updated_assistant


@router.delete("/{assistant_id}/plugins/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_plugin_from_assistant(
    *,
    assistant_id: UUID,
    plugin_id: UUID,
    user_assistant_service: UserAssistantService = Depends(get_user_assistant_service),
):
    """
    Removes the association between a plugin and an assistant.
    """
    await user_assistant_service.remove_plugin_from_assistant(assistant_id, plugin_id)
    return
