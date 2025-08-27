import mimetypes
from contextlib import asynccontextmanager
from importlib.resources import files

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from dingent.core.assistant_manager import get_assistant_manager
from dingent.core.resource_manager import get_resource_manager

from .api_routes import router as admin_config_router

assistant_id = "agent"
FRONTEND_URL = "http://localhost:3000"


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

    # app.state.client = httpx.AsyncClient(base_url=FRONTEND_URL)

    try:
        yield
    finally:
        print("--- Application Shutdown ---")
        try:
            await assistant_manager.aclose()
            # await app.state.client.aclose()
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


def register_frontend_routes(app: FastAPI) -> None:
    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def reverse_proxy(request: Request):
        client: httpx.AsyncClient = request.app.state.client

        # Build the URL for the backend request
        url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))

        # Prepare the request to be forwarded
        rp_request = client.build_request(method=request.method, url=url, headers=request.headers.raw, content=await request.body())

        # Make the request to the frontend server
        # stream=True is crucial for handling large files and streaming responses
        rp_response = await client.send(rp_request, stream=True)

        # Return the response from the frontend server back to the client
        # We use StreamingResponse to efficiently handle the data flow
        return StreamingResponse(
            rp_response.aiter_raw(),
            status_code=rp_response.status_code,
            headers=rp_response.headers,
            background=rp_response.aclose,  # Ensure the connection is closed
        )


def build_agent_api(**kwargs) -> FastAPI:
    kwargs["lifespan"] = lifespan
    app = FastAPI(**kwargs)
    app.include_router(admin_config_router, prefix="/api/v1")
    register_admin_routes(app, "/admin")
    # register_frontend_routes(app)

    @app.get("/api/resource/{resource_id}")
    async def get_resource(resource_id: str, with_model_text=False):
        resource_manager = get_resource_manager()
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
