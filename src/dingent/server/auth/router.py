from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated, Any
from ..security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
# (这个函数可以放在您的 user 模型文件或 service 文件中)
# 暂时我们还是用 FAKE_USERS_DB，但这次会包含哈希后的密码

# 假设这是您运行 get_password_hash("some_password") 后的结果
HASHED_PASSWORD_USER = "$2b$12$DmYECapSrA2wOyBn2xK1sOW4Iqi1T5PtEOZHAyCCE/NmfqvAHTAeG"
HASHED_PASSWORD_ADMIN = "$2b$12$DmYECapSrA2wOyBn2xK1sOW4Iqi1T5PtEOZHAyCCE/NmfqvAHTAeG"

# 更新您的 FAKE_USERS_DB 来存储哈希密码
PROD_FAKE_USERS_DB = {
    "user@example.com": {
        "id": "user_123",
        "email": "user@example.com",
        "hashed_password": HASHED_PASSWORD_USER,
        "role": "user",
        "full_name": "John Doe",
        "username": "saya",
    },
    "admin@example.com": {
        "id": "admin_456",
        "email": "admin@example.com",
        "hashed_password": HASHED_PASSWORD_ADMIN,
        "role": "admin",
        "full_name": "Admin Smith",
        "username": "saya",
    },
}


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict[str, Any]  # 返回一些用户信息给前端


def get_user(db, username: str):
    """根据用户名（这里是 email）查找用户"""
    if username in db:
        return db[username]
    return None


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
