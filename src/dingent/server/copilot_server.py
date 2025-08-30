import os
from contextlib import asynccontextmanager

import uvicorn
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import FastAPI
from langgraph.graph.state import CompiledStateGraph

from .app_factory import app

original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def extended_lifespan(app: FastAPI):
    """
    启动时预构建当前激活 workflow 的图（或 fallback），并注册 CopilotKit endpoint。
    """
    async with original_lifespan(app):
        ctx = app.state.app_context
        gm = ctx.graph_manager
        active_wid = ctx.workflow_manager.active_workflow_id
        graph = await gm.get_graph(active_wid)

        async def _update_copilot_agent_callback(rebuilt_workflow_id: str, new_graph: CompiledStateGraph):
            """
            This function is called by the GraphManager after a rebuild.
            It checks if the rebuilt graph belongs to the currently active workflow
            and updates the SDK's agent if it does.
            """
            # Use a fresh reference to the workflow manager to get the *current* active ID
            current_active_id = ctx.workflow_manager.active_workflow_id

            print(f"Callback triggered for workflow '{rebuilt_workflow_id}'. Current active workflow is '{current_active_id}'.")

            # Only update the agent if the rebuilt graph is for the *active* workflow
            if rebuilt_workflow_id == current_active_id:
                sdk_instance = app.state.copilot_sdk

                new_agent = LangGraphAgent(
                    name="dingent",
                    description="Multi-workflow cached agent graph",
                    graph=new_graph,
                )
                # This is the same hot-swap logic as before
                sdk_instance.agents = [new_agent]

                ctx.log_manager.log_with_context("info", "CopilotKit agent was automatically updated for active workflow.", context={"workflow_id": rebuilt_workflow_id})

        sdk = CopilotKitRemoteEndpoint(
            agents=[
                LangGraphAgent(
                    name="dingent",
                    description="Multi-workflow cached agent graph",
                    graph=graph,
                )
            ],
        )
        app.state.copilot_sdk = sdk
        gm.register_rebuild_callback(_update_copilot_agent_callback)
        add_fastapi_endpoint(app, sdk, "/copilotkit")

        try:
            yield
        finally:
            # 保持缓存常驻；如果需要关闭所有图，可在此解除注释：
            # await gm.close_all()
            pass


app.router.lifespan_context = extended_lifespan


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "dingent.server.copilot_server:app",
        host="0.0.0.0",
        port=port,
    )


if __name__ == "__main__":
    main()
