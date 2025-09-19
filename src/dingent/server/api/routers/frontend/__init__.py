from fastapi import APIRouter
from .resources import router as resources_router
from .threads import router as threads_router

api_router = APIRouter(prefix="/frontend", tags=["frontend"])

api_router.include_router(resources_router)
api_router.include_router(threads_router)
