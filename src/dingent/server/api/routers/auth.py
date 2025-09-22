from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from dingent.server.auth.dependencies import get_current_user
from dingent.server.auth.schemas import LoginResponse
from dingent.server.auth.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from dingent.server.db.crud import authenticate_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # 1. 使用新的 authenticate_user 函数
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 创建一个有时效性的真实 JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # "sub" (subject) 应该是用户的唯一标识符，比如 email 或者 user_id
    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=access_token_expires)
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
