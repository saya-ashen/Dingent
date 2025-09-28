from uuid import UUID
from fastapi import Depends, Request, status
from fastapi.exceptions import HTTPException
from sqlmodel import Session

from dingent.core.analytics_manager import AnalyticsManager
from dingent.core.assistant_manager import AssistantManager
from dingent.core.context import AppContext
from dingent.core.db.models import User
from dingent.core.db.session import get_session
from dingent.core.log_manager import LogManager
from dingent.core.market_service import MarketService
from dingent.core.plugin_manager import PluginManager
from dingent.core.resource_manager import ResourceManager
from dingent.core.workflow_manager import WorkflowManager
from dingent.core.db.crud import assistant as crud_assistant
from ..auth.dependencies import get_current_user


def get_db_session():
    return get_session()


def get_log_manager(
    request: Request,
) -> LogManager:
    """
    Dependency to get the LogManager
    """
    return request.app.state.log_manager


def get_resource_manager(
    log_manager: LogManager = Depends(get_log_manager),
):
    return ResourceManager(log_manager)


def get_plugin_manager(
    request: Request,
    session: Session = Depends(get_db_session),
    log_manager: LogManager = Depends(get_log_manager),
    current_user: User = Depends(get_current_user),
    resource_manager: ResourceManager = Depends(get_resource_manager),
) -> PluginManager:
    """
    Dependency to get the PluginManager.
    """

    registry = request.app.state.plugin_registry
    return PluginManager(
        current_user.id,
        registry,
        resource_manager,
        session,
        log_manager,
    )


def get_assistant_manager(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    log_manager: LogManager = Depends(get_log_manager),
) -> AssistantManager:
    """
    Dependency to get the AssistantManager.
    """
    return AssistantManager(session, current_user.id, plugin_manager, log_manager)


def get_workflow_manager(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    log_manager: LogManager = Depends(get_log_manager),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
):
    return WorkflowManager(
        current_user.id,
        session,
        log_manager,
        assistant_manager,
    )


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


def get_assistant_and_verify_ownership(
    assistant_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    FastAPI Dependency:
    1. Fetches an Assistant by ID using the generic CRUD function.
    2. Raises a 404 if it doesn't exist.
    3. Raises a 403 if the current user is not the owner.
    4. Returns the valid Assistant object if all checks pass.
    """
    # 1. Use the "dumb" CRUD function to get the data
    assistant = crud_assistant.get_assistant(db, assistant_id)

    # 2. Check for existence
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found",
        )

    # 3. Check for ownership -- THIS IS THE KEY STEP
    if assistant.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this assistant",
        )

    # 4. If all is good, return the object
    return assistant
