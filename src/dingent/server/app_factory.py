import os
from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from dingent.core.context import initialize_app_context

from .api import api_router

assistant_id = "agent"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用的生命周期管理器。
    在应用启动时执行 yield 之前的代码。
    在应用关闭时执行 yield 之后的代码。
    """
    print(f"--- Application Startup ---\n{app.summary}")

    print("--- Registered Routes ---")
    app.state.app_context = initialize_app_context()

    try:
        print("Plugins would be initialized here if needed.")
        yield
    finally:
        print("--- Application Shutdown ---")
        try:
            await app.state.app_context.close()
        except Exception as e:
            print(f"Error during assistant_manager.aclose(): {e}")
        print("All plugin subprocesses have been shut down.")


def register_admin_routes(app: FastAPI) -> None:
    static_root = files("dingent").joinpath("static", "admin_dashboard")
    static_root_str = str(static_root)

    # 1. (推荐) /admin -> /admin/ 的重定向
    @app.get("/admin", include_in_schema=False)
    async def admin_redirect():
        return RedirectResponse("/admin/")

    # 2. 核心：智能的 SPA 路由处理器
    @app.get("/admin/{path:path}")
    async def serve_admin_spa(path: str):
        # 确定根 index.html 的路径，作为最终的备用方案
        root_index_path = os.path.join(static_root_str, "index.html")

        # --- 新的、更智能的逻辑 ---

        # Case 1: 检查请求是否直接对应一个文件 (例如: /_next/static/app.js)
        potential_file_path = os.path.join(static_root_str, path)
        if os.path.isfile(potential_file_path):
            return FileResponse(potential_file_path)

        # Case 2: 检查请求是否对应一个页面路由 (例如: /workflows -> workflows.html)
        potential_html_path = os.path.join(static_root_str, f"{path}.html")
        if os.path.isfile(potential_html_path):
            return FileResponse(potential_html_path)

        # Case 3: 检查请求是否是根目录 (path 为空字符串时) 或应该回退到 index.html
        # 对于 /admin/ 的请求, path 会是 ""
        if path == "" or not os.path.splitext(path)[1]:  # 如果路径没有文件扩展名
            return FileResponse(root_index_path)

        # Final Fallback: 如果以上都不匹配，也返回主 index.html
        # 这可以处理带有虚拟子路径的客户端路由，例如 /workflows/123
        return FileResponse(root_index_path)


def build_agent_api(**kwargs) -> FastAPI:
    kwargs["lifespan"] = lifespan
    app = FastAPI(**kwargs)
    app.include_router(api_router, prefix="/api/v1")
    register_admin_routes(app)

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
    "http://localhost:3001",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "https://smith.langchain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许访问的源
    allow_credentials=True,  # 支持 cookie
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)
