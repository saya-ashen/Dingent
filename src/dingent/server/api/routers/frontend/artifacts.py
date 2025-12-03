from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session

from dingent.core.db.models import User
from dingent.core.managers.resource_manager import ResourceManager
from dingent.server.api.dependencies import get_current_user, get_db_session

router = APIRouter()


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
    with_model_text: bool = False,
) -> Response:
    resource_manager: ResourceManager = request.app.state.resource_manager
    resource = resource_manager.get_resource(artifact_id, user.id, session)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

    if not with_model_text:
        content = resource.model_dump_json(exclude={"model_text"})
    else:
        content = resource.model_dump_json()

    return Response(content=content, media_type="application/json", headers={"Cache-Control": "public, max-age=0"})
