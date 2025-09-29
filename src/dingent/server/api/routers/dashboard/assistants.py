from uuid import UUID

from fastapi import APIRouter, Depends, status, Response
from sqlmodel import Session

from dingent.core.db.crud.user import create_test_user
from dingent.core.db.models import Assistant, User
from dingent.core.schemas import AssistantCreate, AssistantRead, AssistantUpdate, PluginAddRequest, PluginUpdateRequest
from dingent.core.services.assistant_service import get_all_assistant_details_for_api, get_assistant_details_for_api
from dingent.server.api.dependencies import (
    get_assistant_and_verify_ownership,
    get_assistant_manager,
    get_current_user,
    get_db_session,
)
from dingent.core.db.crud import assistant as crud_assistant
from dingent.core.managers.assistant_runtime_manager import AssistantRuntimeManager

router = APIRouter(prefix="/assistants", tags=["Assistants"])


@router.get("", response_model=list[AssistantRead])
async def list_assistants(
    session: Session = Depends(get_db_session),
    assistant_manager: AssistantRuntimeManager = Depends(get_assistant_manager),
    user: User = Depends(get_current_user),
) -> list[AssistantRead]:
    assistant_reads = await get_all_assistant_details_for_api(session, assistant_manager, user.id)
    return assistant_reads


@router.post("", response_model=AssistantRead)
async def create_assistant(
    assistant_create: AssistantCreate,
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AssistantRead:
    new_assistant = crud_assistant.create_assistant(session, assistant_create, user.id)
    assistant_read = await get_assistant_details_for_api(session, None, new_assistant.id)
    if assistant_read is None:
        raise Exception("Failed to retrieve assistant details after creation.")
    return assistant_read


@router.patch("/{assistant_id}", response_model=AssistantRead)
async def update_assistant(
    *,
    assistant_update: AssistantUpdate,
    session: Session = Depends(get_db_session),
    assistant: Assistant = Depends(get_assistant_and_verify_ownership),
):
    updated_assistant = crud_assistant.update_assistant(session, assistant, assistant_update)
    return updated_assistant


@router.delete("/{assistant_id}")
async def delete_assistant(
    *,
    session: Session = Depends(get_db_session),
    assistant: Assistant = Depends(get_assistant_and_verify_ownership),
):
    crud_assistant.delete_assistant(db=session, db_assistant=assistant)

    # For a 204 response, you should return nothing. FastAPI handles it.
    # A common way is to return a Response object directly.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{assistant_id}/plugins", response_model=AssistantRead)
async def add_plugin_to_assistant(
    *,
    plugin_add_request: PluginAddRequest,
    session: Session = Depends(get_db_session),
    assistant: Assistant = Depends(get_assistant_and_verify_ownership),
    assistant_manager: AssistantRuntimeManager = Depends(get_assistant_manager),
):
    updated_assistant = crud_assistant.add_plugin_to_assistant(db=session, assistant=assistant, plugin_id=plugin_add_request.plugin_id)
    response_dto = await get_assistant_details_for_api(session, assistant_manager, assistant.id)
    return response_dto


@router.patch("/{assistant_id}/plugins/{plugin_id}", response_model=AssistantRead)
async def update_plugin_on_assistant(
    *,
    plugin_id: UUID,
    plugin_update_request: PluginUpdateRequest,
    session: Session = Depends(get_db_session),
    assistant: Assistant = Depends(get_assistant_and_verify_ownership),
    assistant_manager: AssistantRuntimeManager = Depends(get_assistant_manager),
):
    """
    Updates a plugin's configuration for a specific assistant (e.g., enables/disables it).
    """
    updated_assistant = crud_assistant.update_plugin_for_assistant(db=session, assistant=assistant, plugin_id=plugin_id, update_data=plugin_update_request)

    response_dto = await get_assistant_details_for_api(session, assistant_manager, updated_assistant.id)
    return response_dto


@router.delete("/{assistant_id}/plugins/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_plugin_from_assistant(
    *,
    plugin_id: UUID,
    session: Session = Depends(get_db_session),
    assistant: Assistant = Depends(get_assistant_and_verify_ownership),
):
    """
    Removes the association between a plugin and an assistant.
    """
    crud_assistant.remove_plugin_from_assistant(db=session, assistant=assistant, plugin_id=plugin_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
