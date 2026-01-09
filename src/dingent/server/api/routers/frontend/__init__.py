from fastapi import APIRouter

from .threads import router as threads_router

api_router = APIRouter(tags=["frontend"])

api_router.include_router(threads_router)
