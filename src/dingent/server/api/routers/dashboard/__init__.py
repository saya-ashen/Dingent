from fastapi import APIRouter

from .assistants import router as assistants_router
from .logs import router as logs_router
from .market import router as market_router
from .overview import router as overview_router
from .plugins import router as plugins_router
from .settings import router as settings_router
from .workflows import router as workflows_router


api_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

api_router.include_router(settings_router)
api_router.include_router(assistants_router)
api_router.include_router(workflows_router)
api_router.include_router(plugins_router)
api_router.include_router(logs_router)
api_router.include_router(market_router)
api_router.include_router(overview_router)
