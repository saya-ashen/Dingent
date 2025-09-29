from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from dingent.core.db.crud.user import create_test_user
from dingent.core.schemas import UserRead
from dingent.server.api.dependencies import authenticate_user, get_current_user, get_db_session
from dingent.server.auth.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
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


@router.get("/verify", status_code=status.HTTP_200_OK)
async def verify_token(
    current_user: dict = Depends(get_current_user),
):
    """
    An endpoint to verify a token's validity.
    Accessing this endpoint successfully (i.e., getting a 200 OK response)
    proves the token is valid.
    """
    # If the Depends(get_current_user) succeeds, we know the token is valid.
    # We can just return a success message.
    return {"status": "ok", "message": "Token is valid"}
