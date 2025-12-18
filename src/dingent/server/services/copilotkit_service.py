from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from dingent.core.db.crud.workflow import list_workflows_by_workspace
from dingent.core.db.crud.workspace import get_specific_user_workspace
from dingent.core.db.models import User
from dingent.core.schemas import WorkflowSpec
from dingent.core.workflows.graph_factory import GraphFactory
from dingent.server.copilot.agents import DingLangGraphAGUIAgent


def _truncate(obj: Any, limit: int = 2048) -> Any:
    """Prevent runaway logs by truncating large strings/lists/dicts."""
    if isinstance(obj, str):
        return obj if len(obj) <= limit else (obj[:limit] + f"... <truncated {len(obj) - limit} chars>")
    if isinstance(obj, list):
        if len(obj) > 50:
            head = obj[:25]
            tail = obj[-5:]
            return head + [f"... <{len(obj) - 30} items omitted>"] + tail
        return obj
    if isinstance(obj, dict):
        # Shallow truncate string values only; deep truncation unnecessary in most requests
        out = {}
        for k, v in obj.items():
            out[k] = _truncate(v, limit=limit // 2) if isinstance(v, str | list | dict) else v
        return out
    return obj


def fake_log_method(type, message: str, **kwargs: Any) -> None:
    """A placeholder log method that does nothing."""
    print(type, message, _truncate(kwargs))


class CopilotKitSdk:
    """
    重构后的 Endpoint，更像是一个 Service。
    它不再负责 HTTP 解析，而是专注于业务逻辑：根据 User 和 Session 执行 Agent。
    """

    def __init__(self, *, graph_factory: GraphFactory, checkpointer):
        self.graph_factory = graph_factory
        self.checkpointer = checkpointer

    async def resolve_agent(self, workflow: WorkflowSpec, llm) -> DingLangGraphAGUIAgent:
        graph_artifact = await self.graph_factory.build(workflow, llm, self.checkpointer, fake_log_method)
        return DingLangGraphAGUIAgent(
            name=workflow.name,
            description=workflow.description or f"Agent for workflow '{workflow.name}'",
            graph=graph_artifact.graph,
        )

    def list_agents_for_user(self, user: User, session: Session, workspace_id: UUID | None = None):
        if not workspace_id:
            return []

        workspace = get_specific_user_workspace(session, user.id, workspace_id)
        if not workspace:
            raise HTTPException(status_code=403, detail="Workspace access denied")

        workflows = list_workflows_by_workspace(session, workspace.id)
        agents = {
            wf.name: {
                "name": wf.name,
                "className": wf.name,
                "type": "langgraph",
                "description": wf.description or "",
            }
            for wf in workflows
        }
        default_agent = {
            "default": {
                "name": "unknown",
                "className": "unknown",
                "type": "unknown",
                "description": "Unknown agent",
            }
        }
        # HACK: 这里强制添加一个 default agent，避免前端报错，
        # 但是主要需要限制用户创建这个名称的agent
        agents.update(default_agent)
        return {
            "version": "1.0.0",
            "audioFileTranscriptionEnabled": True,
            "agents": agents,
        }
