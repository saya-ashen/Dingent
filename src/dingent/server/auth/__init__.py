from fastapi import APIRouter
from .router import router

api_router = APIRouter()
api_router.include_router(router)
