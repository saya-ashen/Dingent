from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlmodel import Session

from dingent.core.assistants.assistant_factory import AssistantFactory
from dingent.core.db.session import engine
from dingent.core.logs.log_manager import LogManager
from dingent.core.paths import paths
from dingent.core.plugins.market_service import MarketService
from dingent.core.plugins.plugin_manager import PluginManager
from dingent.core.plugins.plugin_registry import PluginRegistry
from dingent.core.workflows.graph_factory import GraphFactory
from dingent.server.api.schemas import GitHubMarketBackend
from dingent.server.services.copilotkit_service import CopilotKitSdk
from dingent.server.services.plugin_sync_service import PluginSyncService


def _setup_global_services(app: FastAPI):
    """初始化核心服务并挂载到 app.state，返回项目根路径"""

    # 1. 基础服务初始化
    log_manager = LogManager()
    plugin_registry = PluginRegistry(paths.plugins_dir, log_manager)
    plugin_registry.reload_plugins()

    # 2. 数据库同步 (同步操作)
    with Session(engine, expire_on_commit=False) as session:
        PluginSyncService(db_session=session, registry=plugin_registry).sync()

    # 3. 挂载到 App State
    app.state.log_manager = log_manager
    app.state.plugin_registry = plugin_registry
    app.state.plugin_manager = PluginManager(plugin_registry, log_manager)

    market_backend = GitHubMarketBackend(log_manager)
    app.state.market_service = MarketService(paths.plugins_dir, log_manager, market_backend)
    app.state.assistant_factory = AssistantFactory(app.state.plugin_manager, app.state.log_manager)


def create_extended_lifespan(original_lifespan):
    """
    Creates an extended lifespan that adds CopilotKit functionality.
    """

    @asynccontextmanager
    async def extended_lifespan_manager(app: FastAPI):
        async with original_lifespan(app):
            # Phase 1: Initialize Core Services
            _setup_global_services(app)

            async with AsyncSqliteSaver.from_conn_string(paths.sqlite_path.as_posix()) as checkpointer:
                # HACK:
                checkpointer.conn.is_alive = lambda: True
                # 构建 SDK 需要的 factory
                graph_factory = GraphFactory(app.state.assistant_factory)

                # 初始化 SDK 并挂载
                sdk = CopilotKitSdk(graph_factory=graph_factory, checkpointer=checkpointer)
                app.state.copilot_sdk = sdk

                print("--- CopilotKit Extension Initialized ---")
                yield
                print("--- CopilotKit Extension Shutdown ---")

    return extended_lifespan_manager
