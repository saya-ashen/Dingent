from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.graph.state import CompiledStateGraph
from sqlmodel import Session

from dingent.core.db.session import engine
from dingent.core.factories.assistant_factory import AssistantFactory
from dingent.core.managers.log_manager import LogManager
from dingent.core.managers.plugin_manager import PluginManager
from dingent.core.managers.resource_manager import ResourceManager
from dingent.core.services.plugin_registry import PluginRegistry
from dingent.core.utils import find_project_root
from dingent.server.copilot.agents import FixedLangGraphAgent
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
            ctx = app.state.app_context
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
                app.state.resource_manager,
                app.state.log_manager,
            )
            app.state.assistant_factory = AssistantFactory(app.state.plugin_manager, app.state.log_manager)

            # gm = ctx.graph_manager
            # active_wid = ctx.workflow_manager.active_workflow_id
            # graph = await gm.get_graph(active_wid)

            async def _update_copilot_agent_callback(rebuilt_workflow_id: str, new_graph: CompiledStateGraph):
                """
                Callback function triggered by GraphManager after a rebuild.
                Updates the CopilotKit agent if the rebuilt graph belongs to the active workflow.
                """
                current_active_id = ctx.workflow_manager.active_workflow_id

                print(f"Callback triggered for workflow '{rebuilt_workflow_id}'. Current active workflow is '{current_active_id}'.")

                # Only update the agent if the rebuilt graph is for the active workflow
                if rebuilt_workflow_id == current_active_id:
                    sdk_instance = app.state.copilot_sdk

                    new_agent = FixedLangGraphAgent(
                        name="dingent",  # ????? current_active_id?
                        description="Multi-workflow cached agent graph",
                        graph=new_graph,
                    )
                    # Hot-swap the agent
                    sdk_instance.agents = [new_agent]

                    ctx.log_manager.log_with_context("info", "CopilotKit agent was automatically updated for active workflow.", context={"workflow_id": rebuilt_workflow_id})

            # Create CopilotKit SDK with the initial agent
            # setup_copilot_router(app, graph)

            # gm.register_rebuild_callback(_update_copilot_agent_callback)

            print("--- CopilotKit Extension Initialized ---")

            yield

            print("--- CopilotKit Extension Shutdown ---")
            # Cleanup logic can be added here if needed

    return extended_lifespan_manager
