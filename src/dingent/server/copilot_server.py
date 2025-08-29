import os
from contextlib import asynccontextmanager

import uvicorn
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import FastAPI

from dingent.engine.graph import make_graph

from .app_factory import app

original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def extended_lifespan(app: FastAPI):
    """
    在应用启动时，异步创建 graph 并设置 endpoint；
    在应用关闭时，自动处理清理工作。
    """
    async with original_lifespan(app):
        print("Runner-specific startup: Creating graph and setting up endpoint...")

        async with make_graph() as graph:
            sdk = CopilotKitRemoteEndpoint(
                agents=[
                    LangGraphAgent(
                        name="dingent",
                        description="An example agent to use as a starting point for your own agent.",
                        graph=graph,
                    )
                ],
            )

            add_fastapi_endpoint(app, sdk, "/copilotkit")
            # add_langgraph_fastapi_endpoint(
            #     app=app,
            #     agent=LangGraphAGUIAgent(
            #         name="dingent",
            #         description="Describe your agent here, will be used for multi-agent orchestration",
            #         graph=graph,
            #     ),
            #     path="/",  # the endpoint you'd like to serve your agent on
            # )
            yield


app.router.lifespan_context = extended_lifespan


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "dingent.server.copilot_server:app",
        host="0.0.0.0",
        port=port,
    )


if __name__ == "__main__":
    main()
