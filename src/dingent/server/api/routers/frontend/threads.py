from __future__ import annotations
import os
from copilotkit import Agent, CopilotKitContext, LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from copilotkit.sdk import CopilotKitRemoteEndpoint
from fastapi import APIRouter, Depends, FastAPI
from fastapi.exceptions import HTTPException
from sqlalchemy import Engine
from sqlmodel import Session

from dingent.core.factories.graph_factory import GraphFactory
from dingent.core.managers.llm_manager import LLMManager
from time import time
from dingent.server.auth.authorization import dynamic_authorizer
from dingent.server.auth.security import get_current_user_from_token
from dingent.server.copilot.add_fastapi_endpoint import add_fastapi_endpoint
from dingent.server.copilot.agents import FixedLangGraphAgent
from dingent.core.db.crud.workflow import get_workflow_by_name
from dingent.server.copilot.async_copilotkit_remote_endpoint import AsyncCopilotKitRemoteEndpoint

router = APIRouter(dependencies=[Depends(dynamic_authorizer)])


MAX_CACHE_SIZE = 128


from collections import OrderedDict
from typing import Tuple, Any, Callable, cast

Key = Tuple[str, str]  # (user_id, agent_name) or (workflow_id, ...)


def setup_copilot_router(app: FastAPI, graph_factory: GraphFactory, engine: Engine, checkpointer):
    """
    Creates and configures the secure router for CopilotKit and adds it to the application.

    This function is called from within the lifespan manager after the SDK has been initialized.
    """
    print("--- Setting up CopilotKit Secure Router ---")

    # HACK: llm manager
    llm_manager = LLMManager()
    api_key = os.getenv("OPENAI_API_KEY")
    llm = llm_manager.get_llm(
        model_provider="openai",
        model="gpt-4.1",
        api_base="https://www.dmxapi.cn/v1",
        api_key=api_key,
    )

    async def _agents_pipeline(context: CopilotKitContext, name: str) -> Agent:
        token = context.get("properties", {}).get("authorization") or context.get("headers", {}).get("authorization")
        if token and token.startswith("Bearer "):
            token = token[len("Bearer ") :].strip()
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")

        with Session(engine, expire_on_commit=False) as session:
            user = get_current_user_from_token(session, token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid token")

            workflow = get_workflow_by_name(session, name, user.id)
            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
            artifact = await graph_factory.build(workflow, llm, checkpointer)
            return FixedLangGraphAgent(
                name=workflow.name,
                description=f"Agent for workflow '{workflow.name}'",
                graph=artifact.graph,
                langgraph_config={"token": token} if token else {},
            )

    sdk = AsyncCopilotKitRemoteEndpoint(agent_factory=_agents_pipeline, engine=engine)
    # artifact = graph_factory._build_basic(None, llm, checkpointer)
    app.state.copilot_sdk = sdk

    add_fastapi_endpoint(cast(FastAPI, router), sdk, "/copilotkit")

    app.include_router(router, prefix="/api/v1/frontend")

    print("--- CopilotKit Secure Router has been added to the application ---")
