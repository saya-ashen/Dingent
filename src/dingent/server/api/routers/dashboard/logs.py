from fastapi import APIRouter, Depends, HTTPException

from dingent.core.log_manager import LogManager
from dingent.server.api.dependencies import (
    get_log_manager,
)

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("")
async def logs(
    level: str | None = None,
    module: str | None = None,
    limit: int | None = None,
    search: str | None = None,
    log_manager: LogManager = Depends(get_log_manager),
):
    try:
        entries = log_manager.get_logs(level=level, module=module, limit=limit, search=search)
        return [e.to_dict() for e in entries]
    except Exception:
        return []


@router.get("/stats")
async def log_stats(
    log_manager: LogManager = Depends(get_log_manager),
):
    try:
        return log_manager.get_log_stats()
    except Exception:
        raise HTTPException(status_code=404)
