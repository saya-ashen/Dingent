from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated, Any
from .security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, verify_password
from .dependencies import get_user, PROD_FAKE_USERS_DB

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict[str, Any]  # 返回一些用户信息给前端


def authenticate_user(username: str, password: str):
    """
    生产级别的用户认证函数
    1. 从数据库获取用户
    2. 验证密码哈希
    """
    user = get_user(PROD_FAKE_USERS_DB, username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


@router.post("/token", response_model=Token)
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

    # 3. 返回真实的 Token 和一些用户信息
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }
