from fastapi import APIRouter

from .auth import router as auth_router
from .workspace_router import api_router as workspace_router
from .workspaces import router as workspaces_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(workspace_router)
api_router.include_router(workspaces_router)
