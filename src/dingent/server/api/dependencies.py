from uuid import UUID
from fastapi import Depends, Request, status
from fastapi.exceptions import HTTPException
from fastapi.security.oauth2 import OAuth2PasswordBearer
from sqlmodel import Session

from dingent.core.db.crud.user import create_test_user, get_user
from dingent.core.db.models import User
from dingent.core.db.session import engine
from dingent.core.db.crud import assistant as crud_assistant
from dingent.core.managers.plugin_manager import PluginManager
from dingent.core.managers.log_manager import LogManager
from dingent.server.auth.security import decode_token, get_current_user_from_token, verify_password
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlmodel import Session
from fastapi import Depends
from dingent.core.config import settings

from dingent.core.schemas import UserRead
from dingent.server.services.user_assistant_service import UserAssistantService
from dingent.server.services.user_plugin_service import UserPluginService
from dingent.server.services.user_workflow_service import UserWorkflowService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")


def get_db_session():
    with Session(engine, expire_on_commit=False) as session:
        try:
            yield session
            session.commit()  # 只有在路径函数未抛异常时提交
        except Exception:
            session.rollback()
            raise


async def get_current_user(
    session: Session = Depends(get_db_session),
    token: str = Depends(oauth2_scheme),
):
    return get_current_user_from_token(session, token)


def get_log_manager(
    request: Request,
) -> LogManager:
    """
    Dependency to get the LogManager
    """
    return request.app.state.log_manager


def get_resource_manager(
    request: Request,
):
    return request.app.state.resource_manager


def get_plugin_manager(
    request: Request,
) -> PluginManager:
    """
    Dependency to get the PluginManager.
    """
    return request.app.state.plugin_manager


def get_user_assistant_service(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> UserAssistantService:
    """
    Dependency to get the AssistantRuntimeManager.
    """
    assistant_factory = request.app.state.assistant_factory
    return UserAssistantService(user.id, session, assistant_factory)


def get_user_plugin_service(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return UserPluginService(
        user.id,
        session,
        request.app.state.plugin_registry,
        request.app.state.resource_manager,
    )


def get_user_workflow_service(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
    assistant_service: UserAssistantService = Depends(get_user_assistant_service),
    log_manager: LogManager = Depends(get_log_manager),
):
    return UserWorkflowService(
        user_id=user.id,
        session=session,
        assistant_service=assistant_service,
        log_manager=log_manager,
    )


def get_analytics_manager():
    """
    Dependency to get the analyticsManager
    """
    return None


def get_market_service():
    """
    Dependency to get the MarketService.

    Note: The original code initializes this separately. For consistency,
    it's better to manage it within the AppContext as well.
    If you add `self.market_service = MarketService(self.config_manager.project_root)`
    to your AppContext's __init__, this will work seamlessly.
    """


def get_assistant_and_verify_ownership(
    assistant_id: UUID,
    db: Session = Depends(get_db_session),
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
    assistant = crud_assistant.get_assistant_by_id(db=db, id=assistant_id)

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


def get_app_settings():
    return settings


def authenticate_user(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db_session)) -> UserRead:
    """
    生产级别的用户认证函数
    1. 从数据库获取用户
    2. 验证密码哈希
    """
    create_test_user(session)

    user = get_user(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserRead(
        id=str(user.id),
        email=user.email,
        username=user.username,
    )
