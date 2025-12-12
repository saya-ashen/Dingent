from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlmodel import Session

from dingent.core.db.session import engine
from dingent.core.factories.assistant_factory import AssistantFactory
from dingent.core.factories.graph_factory import GraphFactory
from dingent.core.managers.llm_manager import get_llm_service
from dingent.core.managers.log_manager import LogManager
from dingent.core.managers.plugin_manager import PluginManager
from dingent.core.managers.resource_manager import ResourceManager
from dingent.core.services.market_service import GitHubMarketBackend, MarketService
from dingent.core.services.plugin_registry import PluginRegistry
from dingent.core.utils import find_project_root
from dingent.server.copilot.agents import FixedLangGraphAgent
from dingent.server.services.copilotkit_service import AsyncCopilotKitRemoteEndpoint
from dingent.server.services.plugin_sync_service import PluginSyncService


def _setup_global_services(app: FastAPI) -> Path:
    """初始化核心服务并挂载到 app.state，返回项目根路径"""
    project_root = find_project_root()
    assert project_root, "Project root not found."

    # 1. 基础服务初始化
    log_manager = LogManager()
    plugin_registry = PluginRegistry(project_root / "plugins", log_manager)
    plugin_registry.reload_plugins()

    # 2. 数据库同步 (同步操作)
    with Session(engine, expire_on_commit=False) as session:
        PluginSyncService(db_session=session, registry=plugin_registry).sync()

    # 3. 挂载到 App State
    app.state.log_manager = log_manager
    app.state.plugin_registry = plugin_registry
    app.state.resource_manager = ResourceManager(log_manager, max_size=1000)
    app.state.plugin_manager = PluginManager(plugin_registry, log_manager)

    market_backend = GitHubMarketBackend(log_manager)
    app.state.market_service = MarketService(project_root, log_manager, market_backend)
    app.state.assistant_factory = AssistantFactory(app.state.plugin_manager, log_manager)
    app.state.graph_factory = GraphFactory(app.state.assistant_factory)

    return project_root


def _create_agent_factory(app: FastAPI, checkpointer):
    """创建并返回闭包形式的 agent factory"""
    llm = get_llm_service()  # 仅获取一次

    async def factory(workflow, user, session):
        artifact = await app.state.graph_factory.build(user.id, session, app.state.resource_manager, workflow, llm, checkpointer)
        return FixedLangGraphAgent(
            name=workflow.name,
            description=f"Agent for workflow '{workflow.name}'",
            graph=artifact.graph,
            langgraph_config={
                "user": user,
                "assistant_plugin_configs": artifact.assistant_plugin_configs,
            },
        )

    return factory


def create_extended_lifespan(original_lifespan):
    """
    Creates an extended lifespan that adds CopilotKit functionality.
    """

    @asynccontextmanager
    async def extended_lifespan_manager(app: FastAPI):
        async with original_lifespan(app):
            # Phase 1: Initialize Core Services
            project_root = _setup_global_services(app)

            # Phase 2: Initialize Runtime Components (DB & SDK)
            db_path = project_root / ".dingent/data/dingent.db"

            async with AsyncSqliteSaver.from_conn_string(db_path.as_posix()) as checkpointer:
                # 构建 SDK 需要的 factory
                agent_factory = _create_agent_factory(app, checkpointer)

                # 初始化 SDK 并挂载
                sdk = AsyncCopilotKitRemoteEndpoint(agent_factory=agent_factory)
                app.state.copilot_sdk = sdk  # 建议显式挂载，方便 Router 调用

                print("--- CopilotKit Extension Initialized ---")
                yield
                print("--- CopilotKit Extension Shutdown ---")

    return extended_lifespan_manager
