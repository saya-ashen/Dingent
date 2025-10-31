from typing import Any

from fastapi import APIRouter, HTTPException

from dingent.server.api.schemas import AppAdminDetail

router = APIRouter(prefix="/settings", tags=["Settings"])
