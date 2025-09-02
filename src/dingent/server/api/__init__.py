from fastapi import APIRouter

from .routers.assistants import router as assistants_router
from .routers.logs import router as logs_router
from .routers.market import router as market_router
from .routers.overview import router as overview_router
from .routers.plugins import router as plugins_router
from .routers.settings import router as settings_router
from .routers.workflows import router as workflows_router

api_router = APIRouter()

api_router.include_router(settings_router)
api_router.include_router(assistants_router)
api_router.include_router(plugins_router)
api_router.include_router(logs_router)
api_router.include_router(workflows_router)
api_router.include_router(market_router)
api_router.include_router(overview_router)
