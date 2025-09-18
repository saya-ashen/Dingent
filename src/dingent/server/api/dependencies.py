from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from uuid import uuid4 as uuid
from fastapi import Depends, Request

from dingent.core.analytics_manager import AnalyticsManager
from dingent.core.assistant_manager import AssistantManager
from dingent.core.config_manager import ConfigManager
from dingent.core.context import AppContext
from dingent.core.log_manager import LogManager
from dingent.core.market_service import MarketService
from dingent.core.plugin_manager import PluginManager
from dingent.core.workflow_manager import WorkflowManager
from dingent.server.security.models import User


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
    return MarketService(context.config_manager.project_root)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def fake_decode_token(token):
    return User(username="admin_456", email="john@example.com", full_name="John Doe", id=str(uuid()))


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decode_token(token)
    return user
