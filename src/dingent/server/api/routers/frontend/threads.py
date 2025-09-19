from typing import cast
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from copilotkit.sdk import CopilotKitRemoteEndpoint
from fastapi import APIRouter, Depends, FastAPI

from dingent.server.auth.authorization import dynamic_authorizer
from dingent.server.copilot.agents import FixedLangGraphAgent

router = APIRouter(dependencies=[Depends(dynamic_authorizer)])


def setup_copilot_router(app: FastAPI, graph):
    """
    Creates and configures the secure router for CopilotKit and adds it to the application.

    This function is called from within the lifespan manager after the SDK has been initialized.
    """
    print("--- Setting up CopilotKit Secure Router ---")
    # add_langgraph_fastapi_endpoint(
    #     app=cast(FastAPI, router),
    #     agent=LangGraphAGUIAgent(
    #         name="sample_agent",  # the name of your agent defined in langgraph.json
    #         description="Describe your agent here, will be used for multi-agent orchestration",
    #         graph=graph,  # the graph object from your langgraph import
    #     ),
    #     path="/copilotkit",
    # )

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
    add_fastapi_endpoint(cast(FastAPI, router), sdk, "/copilotkit")

    app.include_router(router, prefix="/api/v1/frontend")

    print("--- CopilotKit Secure Router has been added to the application ---")
