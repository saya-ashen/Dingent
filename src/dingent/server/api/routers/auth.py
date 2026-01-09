from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from dingent.core.db.crud.user import create_user, get_user
from dingent.core.workspaces.schemas import UserCreate, UserRead
from dingent.server.api.dependencies import authenticate_user, get_db_session
from dingent.server.auth.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserRead


@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    user: UserRead = Depends(authenticate_user),
):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, session: Session = Depends(get_db_session)):
    """
    用户注册接口
    """
    existing_user = get_user(session, user_in.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email {user_in.email} already registered")

    new_user = create_user(session, user_in)

    return new_user
