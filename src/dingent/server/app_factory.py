import mimetypes
from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from dingent.core.context import get_app_context

from .api_routes import router as admin_config_router

assistant_id = "agent"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用的生命周期管理器。
    在应用启动时执行 yield 之前的代码。
    在应用关闭时执行 yield 之后的代码。
    """
    print(f"--- Application Startup ---\n{app.summary}")

    print("Plugins would be initialized here if needed.")
    app.state.app_context = get_app_context()

    try:
        yield
    finally:
        print("--- Application Shutdown ---")
        try:
            await app.state.app_context.close()
        except Exception as e:
            print(f"Error during assistant_manager.aclose(): {e}")
        print("All plugin subprocesses have been shut down.")


def register_admin_routes(app: FastAPI, base_path: str = "/admin") -> None:
    static_root = files("dingent").joinpath("static", "admin_dashboard")

    def _read_file_bytes(rel_path: str) -> tuple[bytes, str]:
        # 安全处理路径，禁止路径穿越
        rel_path = rel_path.lstrip("/")
        # 先尝试具体文件
        resource = static_root.joinpath(rel_path)
        if getattr(resource, "is_file", lambda: False)():
            data = resource.read_bytes()
            media = mimetypes.guess_type(resource.name)[0] or "application/octet-stream"
            return data, media
        # 回退到 index.html（SPA 兜底）
        index_res = static_root.joinpath("index.html")
        if not getattr(index_res, "is_file", lambda: False)():
            raise FileNotFoundError("index.html not found in admin_dashboard")
        data = index_res.read_bytes()
        return data, "text/html; charset=utf-8"

    @app.get(f"{base_path}", include_in_schema=False)
    @app.get(f"{base_path}/", include_in_schema=False)
    async def admin_index():
        data, media = _read_file_bytes("index.html")
        return Response(content=data, media_type=media)

    @app.get(f"{base_path}" + "/{path:path}", include_in_schema=False)
    async def admin_assets(path: str):
        try:
            data, media = _read_file_bytes(path)
            return Response(content=data, media_type=media, headers={"Cache-Control": "public, max-age=3600"})
        except FileNotFoundError:
            raise HTTPException(404, detail="Not found")


def build_agent_api(**kwargs) -> FastAPI:
    kwargs["lifespan"] = lifespan
    app = FastAPI(**kwargs)
    app.include_router(admin_config_router, prefix="/api/v1")
    register_admin_routes(app, "/admin")

    @app.get("/api/resource/{resource_id}")
    async def get_resource(resource_id: str, request: Request, with_model_text=False):
        app_context = request.app.state.app_context
        resource_manager = app_context.resource_manager
        resource = resource_manager.get(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
        if not with_model_text:
            content = resource.model_dump_json(exclude={"model_text"})
        else:
            content = resource.model_dump_json()
        content_type = "application/json"
        return Response(content=content, media_type=content_type, headers={"Cache-Control": "public, max-age=0"})

    return app


app = build_agent_api()


origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
)
