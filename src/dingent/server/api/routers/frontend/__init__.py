from fastapi import APIRouter

from .artifacts import router as artifacts_router
from .threads import router as threads_router

api_router = APIRouter(prefix="/chat", tags=["frontend"])

api_router.include_router(artifacts_router)
api_router.include_router(threads_router)
