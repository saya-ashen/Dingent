import os
from contextlib import asynccontextmanager

import uvicorn
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from copilotkit import LangGraphAGUIAgent
from dotenv import load_dotenv
from fastapi import FastAPI

from dingent.engine.graph import make_graph

from .app_factory import app

original_lifespan = app.router.lifespan_context

load_dotenv()


@asynccontextmanager
async def extended_lifespan(app: FastAPI):
    """
    在应用启动时，异步创建 graph 并设置 endpoint；
    在应用关闭时，自动处理清理工作。
    """
    async with original_lifespan(app):
        print("Runner-specific startup: Creating graph and setting up endpoint...")

        async with make_graph() as graph:
            add_langgraph_fastapi_endpoint(
                app=app, agent=LangGraphAGUIAgent(name="dingent", description="An example agent to use as a starting point for your own agent.", graph=graph), path="/"
            )

            yield


app.router.lifespan_context = extended_lifespan


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "dingent.server.copilot_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )


# 如果你想通过 `python -m sample_agent.demo` 运行，可以加上这个
if __name__ == "__main__":
    main()
