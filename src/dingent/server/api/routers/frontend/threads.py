import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session, delete, select

from dingent.core.db.crud.workflow import get_workflow_by_name
from dingent.core.db.models import Conversation, User, Workflow, Workspace
from dingent.core.managers.llm_manager import get_llm_service
from dingent.core.schemas import ThreadRead, WorkflowSpec
from dingent.core.workflows.presets import get_fallback_workflow_spec
from dingent.server.api.dependencies import (
    get_current_user,
    get_current_workspace,
    get_db_session,
)
from dingent.server.copilot.agents import DingLangGraphAGUIAgent
from dingent.server.services.copilotkit_service import CopilotKitSdk

router = APIRouter(prefix="/chat", tags=["chat"])


def get_copilot_sdk(request: Request) -> CopilotKitSdk:
    return request.app.state.copilot_sdk


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db_session)]
CopilotSDK = Annotated[CopilotKitSdk, Depends(get_copilot_sdk)]
CurrentWorkspace = Annotated[Workspace, Depends(get_current_workspace)]


@dataclass
class AgentContext:
    """
    这是一个上下文容器，包含执行 Agent 所需的所有准备工作。
    """

    session: DbSession
    agent: DingLangGraphAGUIAgent
    conversation: Conversation
    encoder: EventEncoder
    input_data: RunAgentInput
    assistant_plugin_configs: dict[str, dict] | None


async def get_workflow_spec(workflow: Workflow | None) -> WorkflowSpec:
    if not workflow or not workflow.to_spec().start_node_name:
        return get_fallback_workflow_spec()
    return workflow.to_spec()


async def get_agent_context(
    agent_id: str,
    input_data: RunAgentInput,
    request: Request,
    sdk: CopilotSDK,
    session: DbSession,
    user: CurrentUser,
    workspace: CurrentWorkspace,
) -> AgentContext:
    # --- A. 验证 thread_id ---
    try:
        thread_uuid = uuid.UUID(input_data.thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")

    # --- B. 获取或创建 Conversation (鉴权逻辑) ---
    conversation = session.exec(select(Conversation).where(Conversation.id == thread_uuid)).first()

    if conversation:
        # 鉴权：所有权
        if conversation.user_id != user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to access this conversation.")
        # 鉴权：工作空间隔离
        if conversation.workspace_id != workspace.id:
            raise HTTPException(status_code=403, detail="This conversation belongs to a different workspace.")
    else:
        # 初始化：如果不存在，则创建新会话
        # 注意：这里逻辑复用意味着 /connect 如果传入新 ID 也会创建空会话，这通常是可以接受的
        new_conversation = Conversation(
            id=thread_uuid,
            user_id=user.id,
            workspace_id=workspace.id,
            title="New Chat",
        )
        session.add(new_conversation)
        session.commit()
        session.refresh(new_conversation)
        conversation = new_conversation

    # --- C. 解析 Agent ---
    workflow = get_workflow_by_name(session, agent_id, workspace.id)
    if not workflow and agent_id != "default":
        raise HTTPException(status_code=404, detail=f"Workflow '{agent_id}' not found")

    llm = get_llm_service()
    spec = await get_workflow_spec(workflow)
    agent = await sdk.resolve_agent(spec, llm)

    # --- D. 准备 Encoder ---
    accept_header = request.headers.get("accept")
    encoder = EventEncoder(accept=accept_header)
    assistant_plugin_configs = {}
    for node in spec.nodes:
        for plugin in node.assistant.plugins:
            assistant_plugin_configs[plugin.plugin_id] = plugin.model_dump()

    return AgentContext(
        session=session,
        agent=agent,
        conversation=conversation,
        encoder=encoder,
        input_data=input_data,
        assistant_plugin_configs=assistant_plugin_configs,
    )


@router.post("/info")
@router.get("", response_class=HTMLResponse)
async def handle_info(
    request: Request,
    user: CurrentUser,
    session: DbSession,
    workspace: CurrentWorkspace,
    sdk: CopilotSDK,
):
    """获取可用 Agent 列表"""

    agents = sdk.list_agents_for_user(user, session, workspace_id=workspace.id)

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


@router.get("/info")
async def get_agents(
    session: DbSession,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    sdk: CopilotSDK,
):
    return sdk.list_agents_for_user(user, session, workspace.id)


@router.post("/agent/{agent_id}/run")
async def run(
    ctx: AgentContext = Depends(get_agent_context),
):
    async def event_generator():
        async for event in ctx.agent.run(
            ctx.input_data,
            extra_config={
                "configurable": {
                    "assistant_plugin_configs": ctx.assistant_plugin_configs,
                },
            },
        ):
            yield ctx.encoder.encode(event)

    if ctx.conversation.title == "New Chat":
        ctx.conversation.title = ctx.input_data.messages[0].content[:10]

    ctx.conversation.updated_at = datetime.now(UTC)
    ctx.session.add(ctx.conversation)
    ctx.session.commit()

    return StreamingResponse(event_generator(), media_type=ctx.encoder.get_content_type())


@router.post("/agent/{agent_id}/connect")
async def connect(
    ctx: AgentContext = Depends(get_agent_context),
):
    async def event_generator():
        async for event in ctx.agent.get_thread_messages(ctx.input_data.thread_id, ctx.input_data.run_id):
            yield ctx.encoder.encode(event)

    return StreamingResponse(event_generator(), media_type=ctx.encoder.get_content_type())


@router.get("/threads", response_model=list[ThreadRead])
async def list_threads(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    session: DbSession,
):
    statement = select(Conversation).where(
        Conversation.workspace_id == workspace.id,
        Conversation.user_id == user.id,
    )
    threads = session.exec(statement).all()
    return threads


@router.delete("/threads", status_code=200)
async def delete_all_threads(
    user: CurrentUser,
    workspace: CurrentWorkspace,
    session: DbSession,
):
    """
    删除当前用户在当前工作空间下的所有对话
    """
    # 直接构建 DELETE 语句，效率更高，不需要先 fetch 数据
    statement = delete(Conversation).where(
        Conversation.workspace_id == workspace.id,
        Conversation.user_id == user.id,
    )

    result = session.exec(statement)
    session.commit()

    return {"detail": f"Deleted all threads in workspace. Count: {result.rowcount}"}


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: uuid.UUID,
    user: CurrentUser,
    workspace: CurrentWorkspace,
    session: DbSession,
):
    statement = select(Conversation).where(
        Conversation.id == thread_id,
        Conversation.workspace_id == workspace.id,
        Conversation.user_id == user.id,
    )
    thread = session.exec(statement).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    session.delete(thread)
    session.commit()

    return {"detail": "Thread deleted successfully"}
