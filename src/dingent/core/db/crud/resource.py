from datetime import datetime
from uuid import UUID

from fastapi.exceptions import HTTPException
from sqlmodel import Session

from dingent.core.db.models import Resource
from dingent.core.schemas import ResourceCreate


def create_resource(
    session: Session,
    workspace_id: UUID,
    user_id: UUID,
    payload: ResourceCreate,
) -> Resource:
    """
    新建 Resource。
    """
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")

    db_obj = Resource(
        version=payload.version or "1.0",
        model_text=payload.model_text,
        display=payload.display,
        data=payload.data,
        workspace_id=workspace_id,
        created_by_id=user_id,
        created_at=datetime.utcnow(),
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj
