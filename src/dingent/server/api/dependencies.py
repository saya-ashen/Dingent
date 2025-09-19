import json
import re
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from uuid import uuid4 as uuid
from fastapi import Depends, HTTPException, Request, status

from dingent.core.analytics_manager import AnalyticsManager
from dingent.core.assistant_manager import AssistantManager
from dingent.core.config_manager import ConfigManager
from dingent.core.context import AppContext
from dingent.core.log_manager import LogManager
from dingent.core.market_service import MarketService
from dingent.core.plugin_manager import PluginManager
from dingent.core.workflow_manager import WorkflowManager
from dingent.server.security import decode_token
from ..users.models import User
from ..auth.router import get_user, PROD_FAKE_USERS_DB


FAKE_THREADS_DB = {
    "thread_abc": {"id": "thread_abc", "owner_id": "user_123"},
    "thread_def": {"id": "thread_def", "owner_id": "admin_456"},
}


def get_app_context(request: Request) -> AppContext:
    """
    Dependency to get the AppContext from the application state.
    """
    return request.app.state.app_context


def get_config_manager(context: AppContext = Depends(get_app_context)) -> ConfigManager:
    """
    Dependency to get the ConfigManager.
    """
    return context.config_manager


def get_workflow_manager(context: AppContext = Depends(get_app_context)) -> WorkflowManager:
    """
    Dependency to get the WorkflowManager.
    """
    return context.workflow_manager


def get_assistant_manager(context: AppContext = Depends(get_app_context)) -> AssistantManager:
    """
    Dependency to get the AssistantManager.
    """
    return context.assistant_manager


def get_plugin_manager(context: AppContext = Depends(get_app_context)) -> PluginManager:
    """
    Dependency to get the PluginManager.
    """
    return context.plugin_manager


def get_log_manager(context: AppContext = Depends(get_app_context)) -> LogManager:
    """
    Dependency to get the LogManager
    """
    return context.log_manager


def get_analytics_manager(context: AppContext = Depends(get_app_context)) -> AnalyticsManager:
    """
    Dependency to get the analyticsManager
    """
    return context.analytics_manager


def get_market_service(context: AppContext = Depends(get_app_context)) -> MarketService:
    """
    Dependency to get the MarketService.

    Note: The original code initializes this separately. For consistency,
    it's better to manage it within the AppContext as well.
    If you add `self.market_service = MarketService(self.config_manager.project_root)`
    to your AppContext's __init__, this will work seamlessly.
    """
    # Assuming market_service is now part of the AppContext
    if hasattr(context, "market_service"):
        return context.market_service
    # Fallback to initialize it on the fly if not in context
    return MarketService(context.config_manager.project_root, context.log_manager)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def fake_decode_token(token):
    return User(username="admin_456", email="john@example.com", full_name="John Doe", id=str(uuid()))


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub", "unknown")
    if username is None:
        raise credentials_exception

    user_data = get_user(PROD_FAKE_USERS_DB, username)
    if user_data is None:
        raise credentials_exception

    # 将字典转换为 Pydantic 模型
    return User(**user_data)


async def dynamic_authorizer(request: Request, user: User = Depends(get_current_user)):
    # HACK:
    # 从路径参数中获取子路径，这和原始 handler 的逻辑一致
    path = request.path_params.get("path", "")

    if re.match(r"agent/([a-zA-Z0-9_-]+)/state", path):
        pass

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


class Authorizer:
    def __init__(self, required_permissions: list[str]):
        # e.g., ["agent:read"] or ["agent:execute", "thread:owner"]
        self.required_permissions = set(required_permissions)

    async def __call__(self, request: Request, user: User = Depends(get_current_user)):
        if "agent:read" in self.required_permissions:
            pass  # 允许继续

        if "agent:execute" in self.required_permissions:
            if user.role == "guest":
                raise HTTPException(status_code=403, detail="Anonymous users are not allowed to execute agents.")

        if "thread:owner" in self.required_permissions:
            if user.role == "guest":
                raise HTTPException(status_code=403, detail="You must be logged in to perform this action.")

            try:
                body = await request.json()
                thread_id = body.get("threadId")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON body")

            if not thread_id:
                raise HTTPException(status_code=400, detail="threadId is required for this operation.")

            thread_info = FAKE_THREADS_DB.get(thread_id)
            if not thread_info or thread_info["owner_id"] != user.id:
                raise HTTPException(
                    status_code=404,  # 或者 403 Forbidden
                    detail=f"Thread '{thread_id}' not found or you do not have permission to access it.",
                )
