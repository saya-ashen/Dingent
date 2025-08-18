import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response

from dingent.core.assistant_manager import get_assistant_manager
from dingent.core.resource_manager import get_resource_manager

from .config_routes import router as admin_config_router

assistant_id = "agent"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用的生命周期管理器。
    在应用启动时执行 yield 之前的代码。
    在应用关闭时执行 yield 之后的代码。
    """
    print(f"--- Application Startup ---\n{app.summary}")

    assistant_manager = get_assistant_manager()
    await assistant_manager.get_assistants()

    print("Plugins would be initialized here if needed.")

    try:
        yield
    finally:
        print("--- Application Shutdown ---")
        try:
            await assistant_manager.aclose()
        except Exception as e:
            print(f"Error during assistant_manager.aclose(): {e}")
        print("All plugin subprocesses have been shut down.")


def build_agent_api(**kwargs) -> FastAPI:
    kwargs["lifespan"] = lifespan
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
