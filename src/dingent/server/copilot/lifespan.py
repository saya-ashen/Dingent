import os
from contextlib import asynccontextmanager
from typing import Any, cast

from copilotkit import CopilotKitRemoteEndpoint
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import APIRouter, Depends, FastAPI
from langgraph.graph.state import CompiledStateGraph

from dingent.server.auth.authorization import dynamic_authorizer
from .agents import FixedLangGraphAgent


def create_extended_lifespan(original_lifespan):
    """
    Creates an extended lifespan that adds CopilotKit functionality to the base application.
    """
    @asynccontextmanager
    async def extended_lifespan_manager(app: FastAPI):
        async with original_lifespan(app):
            # Initialize CopilotKit with the application context
            ctx = app.state.app_context
            gm = ctx.graph_manager
            active_wid = ctx.workflow_manager.active_workflow_id
            graph = await gm.get_graph(active_wid)

            async def _update_copilot_agent_callback(rebuilt_workflow_id: str, new_graph: CompiledStateGraph):
                """
                Callback function triggered by GraphManager after a rebuild.
                Updates the CopilotKit agent if the rebuilt graph belongs to the active workflow.
                """
                current_active_id = ctx.workflow_manager.active_workflow_id

                print(f"Callback triggered for workflow '{rebuilt_workflow_id}'. Current active workflow is '{current_active_id}'.")

                # Only update the agent if the rebuilt graph is for the active workflow
                if rebuilt_workflow_id == current_active_id:
                    sdk_instance = app.state.copilot_sdk

                    new_agent = FixedLangGraphAgent(
                        name="dingent",
                        description="Multi-workflow cached agent graph",
                        graph=new_graph,
                    )
                    # Hot-swap the agent
                    sdk_instance.agents = [new_agent]

                    ctx.log_manager.log_with_context(
                        "info", 
                        "CopilotKit agent was automatically updated for active workflow.", 
                        context={"workflow_id": rebuilt_workflow_id}
                    )

            # Create CopilotKit SDK with the initial agent
            sdk = CopilotKitRemoteEndpoint(
                agents=[
                    FixedLangGraphAgent(
                        name="dingent",
                        description="Multi-workflow cached agent graph",
                        graph=graph,
                    )
                ],
            )
            app.state.copilot_sdk = sdk
            
            # Set up secure router with authorization
            secure_router = APIRouter(dependencies=[Depends(dynamic_authorizer)])
            add_fastapi_endpoint(cast(FastAPI, secure_router), sdk, "/copilotkit")
            
            # Register the rebuild callback and include the router
            gm.register_rebuild_callback(_update_copilot_agent_callback)
            app.include_router(secure_router)

            print("--- CopilotKit Extension Initialized ---")

            yield

            print("--- CopilotKit Extension Shutdown ---")
            # Cleanup logic can be added here if needed

    return extended_lifespan_manager
