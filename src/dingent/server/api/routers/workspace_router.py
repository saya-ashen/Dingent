from fastapi import APIRouter
from .dashboard import api_router as dashboard_router
from .frontend import api_router as frontend_router


api_router = APIRouter(prefix="/{workspace_slug}")
api_router.include_router(dashboard_router)
api_router.include_router(frontend_router)
