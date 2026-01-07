import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, cast

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session, delete, select

from dingent.core.db.crud.workflow import get_workflow_by_name
from dingent.core.db.models import Conversation, User, Workflow, Workspace
from dingent.core.managers.llm_manager import get_llm_service
from dingent.core.schemas import ThreadRead, ExecutableWorkflow
from dingent.core.workflows.presets import get_fallback_workflow_spec
from dingent.server.api.dependencies import (
    get_current_user,
    get_current_user_optional,
    get_current_workspace,
    get_current_workspace_allow_guest,
    get_db_session,
)
from dingent.server.copilot.agents import DingLangGraphAGUIAgent
from dingent.server.services.copilotkit_service import CopilotKitSdk

router = APIRouter(prefix="/chat", tags=["chat"])


def get_copilot_sdk(request: Request) -> CopilotKitSdk:
    return request.app.state.copilot_sdk


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
DbSession = Annotated[Session, Depends(get_db_session)]
CopilotSDK = Annotated[CopilotKitSdk, Depends(get_copilot_sdk)]
CurrentWorkspace = Annotated[Workspace, Depends(get_current_workspace)]
CurrentWorkspaceAllowGuest = Annotated[Workspace, Depends(get_current_workspace_allow_guest)]


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


def update_conversation_title(conversation: Conversation, input_data: RunAgentInput, max_length: int = 50) -> None:
    """
    Update conversation title based on first message if title is "New Chat".

    Args:
        conversation: The conversation object to update
        input_data: The input data containing messages
        max_length: Maximum length for the title (default: 50)
    """
    if conversation.title == "New Chat" and input_data.messages:
        conversation.title = cast(str, input_data.messages[0].content)[:max_length]


async def get_workflow_spec(workflow: Workflow | None) -> ExecutableWorkflow:
    if not workflow or not workflow.to_spec().start_node:
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
    encoder = EventEncoder(accept=cast(str, accept_header))
    assistant_plugin_configs = {}
    for config in spec.assistant_configs.values():
        for plugin in config.plugins:
            assistant_plugin_configs[plugin.plugin_id] = plugin.model_dump()

    return AgentContext(
        session=session,
        agent=agent,
        conversation=conversation,
        encoder=encoder,
        input_data=input_data,
        assistant_plugin_configs=assistant_plugin_configs,
    )


async def get_agent_context_allow_guest(
    agent_id: str,
    input_data: RunAgentInput,
    request: Request,
    sdk: CopilotSDK,
    session: DbSession,
    user: CurrentUserOptional,
    workspace: CurrentWorkspaceAllowGuest,
    visitor_id: str | None = Header(None, alias="X-Visitor-ID"),
) -> AgentContext:
    """
    获取 Agent 上下文，支持游客模式。
    游客通过 X-Visitor-ID header 提供唯一标识符。
    """
    # --- A. 验证 thread_id ---
    try:
        thread_uuid = uuid.UUID(input_data.thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")

    # --- B. 获取或创建 Conversation (支持游客) ---
    conversation = session.exec(select(Conversation).where(Conversation.id == thread_uuid)).first()

    if conversation:
        # 鉴权逻辑：区分登录用户和游客
        if user:
            # 已登录用户：验证所有权
            if conversation.user_id != user.id:
                raise HTTPException(status_code=403, detail="You do not have permission to access this conversation.")
        else:
            # 游客模式：验证 visitor_id
            if not visitor_id:
                raise HTTPException(status_code=400, detail="Guest users must provide X-Visitor-ID header")
            if conversation.visitor_id != visitor_id:
                raise HTTPException(status_code=403, detail="You do not have permission to access this conversation.")

        # 工作空间隔离验证（对所有用户适用）
        if conversation.workspace_id != workspace.id:
            raise HTTPException(status_code=403, detail="This conversation belongs to a different workspace.")
    else:
        # 创建新会话
        if user:
            # 已登录用户
            new_conversation = Conversation(
                id=thread_uuid,
                user_id=user.id,
                workspace_id=workspace.id,
                title="New Chat",
            )
        else:
            # 游客模式
            if not visitor_id:
                raise HTTPException(status_code=400, detail="Guest users must provide X-Visitor-ID header")
            new_conversation = Conversation(
                id=thread_uuid,
                user_id=None,
                visitor_id=visitor_id,
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
    encoder = EventEncoder(accept=cast(str, accept_header))
    assistant_plugin_configs = {}
    for config in spec.assistant_configs.values():
        for plugin in config.plugins:
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

    # Get response data from SDK (includes version, agents, etc.)
    response_data = sdk.list_agents_for_user(user, session, workspace_id=workspace.id)

    # Add additional fields required by CopilotKit protocol
    response_data["actions"] = []  # 暂时为空
    response_data["sdkVersion"] = "0.1.0"

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        from copilotkit.html import generate_info_html

        return HTMLResponse(content=generate_info_html(cast(Any, response_data)))

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
            yield ctx.encoder.encode(cast(Any, event))

    # Update conversation title if needed
    update_conversation_title(ctx.conversation, ctx.input_data)

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
            yield ctx.encoder.encode(cast(Any, event))

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


# --- Guest Mode Endpoints ---


@router.post("/guest/info")
@router.get("/guest/info", response_class=HTMLResponse)
async def handle_info_guest(
    request: Request,
    user: CurrentUserOptional,
    session: DbSession,
    workspace: CurrentWorkspaceAllowGuest,
    sdk: CopilotSDK,
):
    """获取可用 Agent 列表 (游客模式)"""

    # Get response data from SDK (includes version, agents, etc.)
    response_data = sdk.list_agents_for_user(user, session, workspace_id=workspace.id)

    # Add additional fields required by CopilotKit protocol
    response_data["actions"] = []  # 暂时为空
    response_data["sdkVersion"] = "0.1.0"

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        from copilotkit.html import generate_info_html

        return HTMLResponse(content=generate_info_html(cast(Any, response_data)))

    return response_data


@router.post("/guest/agent/{agent_id}/run")
async def run_guest(
    ctx: AgentContext = Depends(get_agent_context_allow_guest),
):
    """运行 Agent (游客模式)"""

    async def event_generator():
        async for event in ctx.agent.run(
            ctx.input_data,
            extra_config={
                "configurable": {
                    "assistant_plugin_configs": ctx.assistant_plugin_configs,
                },
            },
        ):
            yield ctx.encoder.encode(cast(Any, event))

    # Update conversation title if needed
    update_conversation_title(ctx.conversation, ctx.input_data)

    ctx.conversation.updated_at = datetime.now(UTC)
    ctx.session.add(ctx.conversation)
    ctx.session.commit()

    return StreamingResponse(event_generator(), media_type=ctx.encoder.get_content_type())


@router.post("/guest/agent/{agent_id}/connect")
async def connect_guest(
    ctx: AgentContext = Depends(get_agent_context_allow_guest),
):
    """连接到已存在的对话 (游客模式)"""

    async def event_generator():
        async for event in ctx.agent.get_thread_messages(ctx.input_data.thread_id, ctx.input_data.run_id):
            yield ctx.encoder.encode(cast(Any, event))

    return StreamingResponse(event_generator(), media_type=ctx.encoder.get_content_type())


@router.get("/guest/threads", response_model=list[ThreadRead])
async def list_threads_guest(
    user: CurrentUserOptional,
    workspace: CurrentWorkspaceAllowGuest,
    session: DbSession,
    visitor_id: str | None = Header(None, alias="X-Visitor-ID"),
):
    """列出游客的对话历史"""
    breakpoint()
    if user:
        # 已登录用户
        statement = select(Conversation).where(
            Conversation.workspace_id == workspace.id,
            Conversation.user_id == user.id,
        )
    else:
        # 游客模式
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Guest users must provide X-Visitor-ID header")
        statement = select(Conversation).where(
            Conversation.workspace_id == workspace.id,
            Conversation.visitor_id == visitor_id,
        )

    threads = session.exec(statement).all()
    return threads


@router.delete("/guest/threads/{thread_id}")
async def delete_thread_guest(
    thread_id: uuid.UUID,
    user: CurrentUserOptional,
    workspace: CurrentWorkspaceAllowGuest,
    session: DbSession,
    visitor_id: str | None = Header(None, alias="X-Visitor-ID"),
):
    """删除游客的单个对话"""
    if user:
        # 已登录用户
        statement = select(Conversation).where(
            Conversation.id == thread_id,
            Conversation.workspace_id == workspace.id,
            Conversation.user_id == user.id,
        )
    else:
        # 游客模式
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Guest users must provide X-Visitor-ID header")
        statement = select(Conversation).where(
            Conversation.id == thread_id,
            Conversation.workspace_id == workspace.id,
            Conversation.visitor_id == visitor_id,
        )

    thread = session.exec(statement).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    session.delete(thread)
    session.commit()

    return {"detail": "Thread deleted successfully"}
