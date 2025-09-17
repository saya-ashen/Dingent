import json
import re
from typing import Annotated
from uuid import uuid4 as uuid

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def fake_decode_token(token):
    return User(username="admin_456", email="john@example.com", full_name="John Doe", id=str(uuid()))


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decode_token(token)
    return user


FAKE_USERS_DB = {
    "user_123": {"id": "user_123", "role": "user", "name": "abc"},
    "admin_456": {"id": "admin_456", "role": "admin", "name": "def"},
}

FAKE_API_KEYS_DB = {
    "secret-user-key": FAKE_USERS_DB["user_123"],
    "secret-admin-key": FAKE_USERS_DB["admin_456"],
}

FAKE_THREADS_DB = {
    "thread_abc": {"id": "thread_abc", "owner_id": "user_123"},
    "thread_def": {"id": "thread_def", "owner_id": "admin_456"},
}


class Authorizer:
    def __init__(self, required_permissions: list[str]):
        # e.g., ["agent:read"] or ["agent:execute", "thread:owner"]
        self.required_permissions = set(required_permissions)

    async def __call__(self, request: Request, user: User = Depends(get_current_user)):
        # --- 1. 基于角色的权限检查 ---
        # 匿名用户只能读取
        if "agent:read" in self.required_permissions:
            # 任何用户（包括匿名）都有读取权限
            pass  # 允许继续

        # 执行权限需要非匿名用户
        if "agent:execute" in self.required_permissions:
            if user.role == "guest":
                raise HTTPException(status_code=403, detail="Anonymous users are not allowed to execute agents.")

        # --- 2. 基于资源所有权的权限检查 ---
        if "thread:owner" in self.required_permissions:
            if user.role == "guest":
                raise HTTPException(status_code=403, detail="You must be logged in to perform this action.")

            # 从请求体中安全地获取 threadId
            try:
                # 注意：直接在依赖项中读取 request.json() 可能会消耗掉请求体，
                # 导致后续的路径操作函数无法再次读取。
                # 但在你提供的代码中，所有逻辑都在一个 handler 里，
                # 我们可以在这里读取并传递。
                body = await request.json()
                thread_id = body.get("threadId")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON body")

            if not thread_id:
                # 如果是需要验证所有权但客户端没提供 threadId，则可能是个坏请求
                # 或者是一个新线程，取决于你的业务逻辑
                # 这里我们假设它必须提供
                raise HTTPException(status_code=400, detail="threadId is required for this operation.")

            thread_info = FAKE_THREADS_DB.get(thread_id)
            if not thread_info or thread_info["owner_id"] != user.id:
                raise HTTPException(
                    status_code=404,  # 或者 403 Forbidden
                    detail=f"Thread '{thread_id}' not found or you do not have permission to access it.",
                )

        # 所有检查通过


async def dynamic_authorizer(request: Request, user: User = Depends(get_current_user)):
    # HACK:
    # 从路径参数中获取子路径，这和原始 handler 的逻辑一致
    path = request.path_params.get("path", "")

    # --- 在这里镜像 handler 函数的路由逻辑 ---

    # 规则1: 匹配 /agent/{name}/state (获取状态)
    if re.match(r"agent/([a-zA-Z0-9_-]+)/state", path):
        # 权限要求: 允许匿名读取
        # 这里我们什么都不做，直接通过
        pass

    # 规则2: 匹配 /agent/{name} (执行)
    elif re.match(r"agent/([a-zA-Z0-9_-]+)", path):
        # 权限要求: 必须是登录用户，且是线程所有者
        if user.role == "anonymous":
            raise HTTPException(status_code=403, detail="Anonymous users are not allowed to execute agents.")

        # 检查线程所有权
        try:
            body = await request.json()
            thread_id = body.get("threadId")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body for execution request.")

        if not thread_id:
            # 根据业务逻辑，执行时可能允许创建新线程，所以 threadId 可能为空
            # 这里我们假设如果提供了 thread_id，就必须验证所有权
            pass
        else:
            thread_info = FAKE_THREADS_DB.get(thread_id)
            if not thread_info or thread_info["owner_id"] != user.id:
                raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found or you do not have permission to access it.")

    # 规则3: 匹配 /action/{name} (执行动作)
    elif re.match(r"action/([a-zA-Z0-9_-]+)", path):
        # 权限要求: 必须是登录用户
        if user.role == "anonymous":
            raise HTTPException(status_code=403, detail="Anonymous users are not allowed to execute actions.")

    # 默认规则: 如果没有匹配到特定规则，可以根据需要放行或拒绝
    # 在这里我们默认放行，因为可能还有其他路径（如 info）
    else:
        pass

    # 所有检查都通过了
    return user
