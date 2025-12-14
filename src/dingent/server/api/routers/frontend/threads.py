import inspect
from collections.abc import Awaitable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session

from dingent.core.db.crud.workflow import get_workflow_by_name
from dingent.core.db.models import User, Workspace
from dingent.server.api.dependencies import (
    get_current_user,
    get_current_workspace,
    get_db_session,
)
from dingent.server.api.schemas import AgentExecuteRequest, AgentStateRequest
from dingent.server.services.copilotkit_service import AsyncCopilotKitRemoteEndpoint

router = APIRouter()


async def _maybe_await[T](value: T | Awaitable[T]) -> T:
    return await value if inspect.isawaitable(value) else value  # type: ignore[return-value]


def get_copilot_sdk(request: Request) -> AsyncCopilotKitRemoteEndpoint:
    return request.app.state.copilot_sdk


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db_session)]
CopilotSDK = Annotated[AsyncCopilotKitRemoteEndpoint, Depends(get_copilot_sdk)]
CurrentWorkspace = Annotated[Workspace, Depends(get_current_workspace)]


@router.get("/", response_class=HTMLResponse)
@router.post("/info")
async def handle_info(
    request: Request,
    user: CurrentUser,
    session: DbSession,
    workspace: CurrentWorkspace,
    sdk: CopilotSDK,
):
    """获取可用 Agent 列表"""

    agents = await sdk.list_agents_for_user(user, session, workspace_id=workspace.id)

    # 构造符合 CopilotKit 协议的返回
    response_data = {
        "agents": agents,
        "actions": [],  # 暂时为空
        "sdkVersion": "0.1.0",
    }

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        from copilotkit.html import generate_info_html

        return HTMLResponse(content=generate_info_html(response_data))

    return response_data


@router.post("/agent/{name}")
async def execute_agent(
    name: str,
    body: AgentExecuteRequest,
    user: CurrentUser,
    session: DbSession,
    sdk: CopilotSDK,
):
    """执行 Agent"""
    events = await sdk.execute_agent_with_user(
        user=user,
        session=session,
        name=name,
        thread_id=body.threadId,
        state=body.state,
        messages=body.messages,
        actions=body.actions,
        node_name=body.nodeName,
        config=body.config,
        meta_events=body.metaEvents,
    )

    return StreamingResponse(events, media_type="application/json")


@router.post("/agent/{name}/state")
async def get_agent_state(
    name: str,
    body: AgentStateRequest,
    user: CurrentUser,
    session: DbSession,
    sdk: CopilotSDK,
):
    """获取 Agent 状态"""
    workflow = get_workflow_by_name(session, name, user.id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    agent = await sdk._resolve_agent(workflow, user, session)

    sdk._log_request_info(
        title="Handling get agent state request (factory-based agents)",
        data=[
            ("Agent", agent.dict_repr()),
            ("Thread ID", body.threadId),
        ],
    )

    state = agent.get_state(thread_id=body.threadId)
    return await _maybe_await(state)
