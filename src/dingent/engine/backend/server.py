import json

from fastapi import FastAPI, HTTPException, Response

from ..backend.resource_manager import get_resource_manager
from .admin.config.server import router as admin_config_router

assistant_id = "agent"


def build_agent_api(**kwargs) -> FastAPI:
    app = FastAPI(**kwargs)
    app.include_router(admin_config_router)

    @app.get("/api/resource/{resource_id}")
    async def get_resource(resource_id: str):
        resource_manager = get_resource_manager()
        resource = resource_manager.get(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
        content = json.dumps(resource)
        content_type = "application/json"
        return Response(content=content, media_type=content_type, headers={"Cache-Control": "public, max-age=0"})

    return app
