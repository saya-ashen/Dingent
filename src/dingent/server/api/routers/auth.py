from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated

FAKE_USERS_DB = {
    "user_123@user.com": {"id": "user_123", "role": "user", "name": "abc"},
    "admin_456@admin.com": {"id": "admin_456", "role": "admin", "name": "def"},
}


# --- 假设这是你的认证工具函数 ---
# 在实际应用中，你需要使用像 passlib 和 pyjwt 这样的库
def verify_password(plain_password, hashed_password):
    # 这是一个模拟实现，实际应用中你需要用 passlib 验证
    # 比如 return pwd_context.verify(plain_password, hashed_password)
    return FAKE_USERS_DB.get(hashed_password, {}).get("password") == plain_password


def create_access_token(data: dict):
    # 这是一个模拟实现，实际应用中你需要用 jose.jwt 或 pyjwt 生成真实的 JWT
    # 比如 to_encode = data.copy(); ...; encoded_jwt = jwt.encode(...)
    return f"fake-jwt-token-for-{data.get('sub')}"


def authenticate_user(username: str, password: str):
    # 在这个模拟系统中，我们假设 username 就是 user_id
    user_info = FAKE_USERS_DB.get(username)
    if not user_info:
        return False
    # 假设密码也存储在 FAKE_USERS_DB 中，或者你有其他验证方式
    # if not verify_password(password, user_info["hashed_password"]):
    #    return False
    # 这里为了简单，我们直接返回用户信息
    return user_info


router = APIRouter(prefix="/auth", tags=["Authentication"])


class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # authenticate_user 会根据用户名（这里是 user_id）和密码去验证
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="不正确的用户名或密码",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建 access token
    # "sub" 是 JWT 的标准字段，代表 "subject" (主题)，通常是用户的唯一标识符
    access_token = create_access_token(data={"sub": user["id"]})

    return {"access_token": access_token, "token_type": "bearer"}
