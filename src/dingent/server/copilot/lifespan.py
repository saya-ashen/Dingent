from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlmodel import Session

from dingent.core.db.session import engine
from dingent.core.factories.assistant_factory import AssistantFactory
from dingent.core.factories.graph_factory import GraphFactory
from dingent.core.managers.log_manager import LogManager
from dingent.core.managers.plugin_manager import PluginManager
from dingent.core.managers.resource_manager import ResourceManager
from dingent.core.services.plugin_registry import PluginRegistry
from dingent.core.utils import find_project_root
from dingent.server.services.plugin_sync_service import PluginSyncService

from ..api.routers.frontend.threads import setup_copilot_router


def create_extended_lifespan(original_lifespan):
    """
    Creates an extended lifespan that adds CopilotKit functionality to the base application.
    """

    @asynccontextmanager
    async def extended_lifespan_manager(app: FastAPI):
        async with original_lifespan(app):
            # Initialize CopilotKit with the application context
            project_root = find_project_root()
            assert project_root is not None, "Project root not found."
            app.state.log_manager = LogManager()
            plugin_registry = PluginRegistry(project_root / "plugins", app.state.log_manager)
            plugin_registry.reload_plugins()
            with Session(engine, expire_on_commit=False) as session:
                sync_service = PluginSyncService(db_session=session, registry=plugin_registry)
                sync_service.sync()

            app.state.plugin_registry = plugin_registry
            app.state.resource_manager = ResourceManager(app.state.log_manager, max_size=1000)
            app.state.plugin_manager = PluginManager(
                app.state.plugin_registry,
                app.state.log_manager,
            )
            app.state.assistant_factory = AssistantFactory(app.state.plugin_manager, app.state.log_manager)

            app.state.graph_factory = GraphFactory(
                app.state.assistant_factory,
            )
            db_path = project_root / ".dingent/data/dingent.db"
            async with AsyncSqliteSaver.from_conn_string(db_path.as_posix()) as checkpointer:
                setup_copilot_router(app, app.state.graph_factory, engine, checkpointer, app.state.resource_manager)

                print("--- CopilotKit Extension Initialized ---")

                yield

                print("--- CopilotKit Extension Shutdown ---")
            # Cleanup logic can be added here if needed

    return extended_lifespan_manager
