from .routers import api_router


@api_router.get("/health")
def health():
    return {"status": "ok"}


__all__ = ["api_router"]
