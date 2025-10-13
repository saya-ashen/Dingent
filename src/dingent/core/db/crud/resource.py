from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi.exceptions import HTTPException
from sqlmodel import Session, select

from dingent.core.db.models import Plugin, Resource
from dingent.core.schemas import ResourceCreate


def create_resource(
    user_id: UUID,
    session: Session,
    payload: ResourceCreate,
) -> Resource:
    """
    新建 Resource。
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    db_obj = Resource(
        version=payload.version or "1.0",
        model_text=payload.model_text,
        display=payload.display,
        data=payload.data,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj
