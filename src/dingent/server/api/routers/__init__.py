from fastapi import APIRouter
from .dashboard import api_router as dashboard_router
from .frontend import api_router as frontend_router
from .auth import router as auth_router

api_router = APIRouter()

api_router.include_router(dashboard_router)
api_router.include_router(frontend_router)
api_router.include_router(auth_router)
