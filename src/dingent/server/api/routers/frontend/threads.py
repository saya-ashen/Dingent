from __future__ import annotations

import os

from copilotkit import Agent
from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine
from sqlmodel import Session

from dingent.core.db.models import User, Workflow
from dingent.core.factories.graph_factory import GraphFactory
from dingent.core.managers.llm_manager import LLMManager
from dingent.core.managers.resource_manager import ResourceManager
from dingent.server.copilot.add_fastapi_endpoint import add_fastapi_endpoint
from dingent.server.copilot.agents import FixedLangGraphAgent
from dingent.server.copilot.async_copilotkit_remote_endpoint import AsyncCopilotKitRemoteEndpoint

router = APIRouter()


def setup_copilot_router(app: FastAPI, graph_factory: GraphFactory, engine: Engine, checkpointer, resource_manager: ResourceManager):
    """
    Creates and configures the secure router for CopilotKit and adds it to the application.

    This function is called from within the lifespan manager after the SDK has been initialized.
    """
    print("--- Setting up CopilotKit Secure Router ---")

    # HACK: llm manager
    llm_manager = LLMManager()
    api_key = os.getenv("GEMINI_API_KEY")
    llm = llm_manager.get_llm(
        model="gemini/gemini-2.5-flash",
        # api_base="https://www.dmxapi.cn/v1",
        api_key=api_key,
    )

    async def _agents_pipeline(workflow: Workflow, user: User, session: Session) -> Agent:
        artifact = await graph_factory.build(user.id, session, resource_manager, workflow, llm, checkpointer)
        return FixedLangGraphAgent(
            name=workflow.name,
            description=f"Agent for workflow '{workflow.name}'",
            graph=artifact.graph,
            langgraph_config={
                "user": user,
                "assistant_plugin_configs": artifact.assistant_plugin_configs,
            },
        )

    sdk = AsyncCopilotKitRemoteEndpoint(agent_factory=_agents_pipeline, engine=engine)
    app.state.copilot_sdk = sdk

    add_fastapi_endpoint(router, sdk, "/copilotkit")

    app.include_router(router, prefix="/api/v1/frontend")

    print("--- CopilotKit Secure Router has been added to the application ---")
