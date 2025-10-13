from __future__ import annotations
from uuid import UUID
import uuid

from sqlmodel import Session

from dingent.core.db.models import Workflow, WorkflowNode
from dingent.core.factories.assistant_factory import AssistantFactory
from dingent.core.managers.resource_manager import ResourceManager

"""
Workflow → LangGraph Transform Factory
-------------------------------------

This module factors out the *pure transformation* from a domain `Workflow`
object into a compiled LangGraph graph. It is intentionally stateless and
side‑effect–free except for allocating resources (checkpointer, assistant
sub‑graphs) that are returned to the caller as part of the `GraphArtifact` so
the caller can manage lifecycle explicitly.

Drop‑in usage for your current GraphManager:

    factory = GraphFactory(app_context)
    artifact = await factory.build(workflow_or_id)
    graph = artifact.graph  # CompiledStateGraph

The `GraphArtifact` also includes the `AsyncExitStack` holding resources and the
`checkpointer`. The caller should either keep the `artifact` around (and call
`await artifact.aclose()` when done) or move the stack into its own cache entry.

Design goals:
- Separate concerns (transform vs. cache/orchestration)
- Small, composable API
- Clear fallback path when workflow is missing or invalid
- Minimal coupling to the broader app; dependency injection through `AppContextSubset`
"""

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Any, Optional

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from dingent.engine.graph import (
    MainState,
    _normalize_name,
    create_assistant_graphs,
    get_safe_swarm,
)
from langgraph_swarm import create_swarm


# ==============================================================================
# Public Artifacts
# ==============================================================================


@dataclass
class GraphArtifact:
    """Bundle of the compiled graph and its managed resources.

    Note: `checkpointer` is a *shared* saver across all graphs. Do not close it
    from this artifact; use `GraphFactory.aclose()` at shutdown.
    """

    workflow_id: UUID
    graph: CompiledStateGraph
    stack: AsyncExitStack
    checkpointer: Any
    default_active_agent: Optional[str]

    async def aclose(self) -> None:
        """Close all resources held by the artifact."""
        await self.stack.aclose()


# ==============================================================================
# Factory
# ==============================================================================


def fake_log(level, messages="", context={}, *args, **kwargs):
    print(f"[GraphFactory] [{level.upper()}] {messages} | {context}")


class GraphFactory:
    def __init__(self, assistant_factory: AssistantFactory):
        self._log = fake_log
        self.assistant_factory = assistant_factory

    async def build(
        self,
        user_id: UUID,
        session: Session,
        resource_manager: ResourceManager,
        workflow: Workflow,
        llm,
        checkpointer,
    ) -> GraphArtifact:
        """Transform a domain `Workflow`  → compiled LangGraph.

        Fallback to a minimal single‑LLM chat graph when workflow is missing or
        has no valid start node.
        """
        workflow_id = workflow.id

        stack = AsyncExitStack()

        if not workflow or not _get_start_node(workflow):
            self._log("warning", "Workflow invalid or not found; using basic fallback.", context={"wf": workflow_id})
            return self._build_basic(stack, llm, checkpointer)

        return await self._build_full(user_id, session, resource_manager, workflow, stack, llm, checkpointer)

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_basic(self, stack: AsyncExitStack, llm, checkpointer) -> GraphArtifact:
        wf_id = uuid.uuid4()
        self._log("info", "Building basic fallback graph.", context={"wf": wf_id})

        def basic_chatbot(state: MainState):
            return {"messages": [llm.invoke(state["messages"])]}

        graph = StateGraph(MainState)
        graph.add_node("basic_chatbot", basic_chatbot)
        graph.add_edge(START, "basic_chatbot")
        graph.add_edge("basic_chatbot", END)

        compiled = graph.compile(checkpointer)
        compiled.name = "agent"

        return GraphArtifact(
            workflow_id=wf_id,
            graph=compiled,
            stack=stack,
            checkpointer=checkpointer,
            default_active_agent=None,
        )

    async def _build_full(
        self,
        user_id: UUID,
        session: Session,
        resource_manager: ResourceManager,
        workflow: Workflow,
        stack: AsyncExitStack,
        llm,
        checkpointer,
    ) -> GraphArtifact:
        self._log("info", "Building graph for workflow.", context={"wf": workflow.id})

        start_node = _get_start_node(workflow)
        if not start_node:
            raise ValueError(f"Workflow '{workflow.id}' has no start node.")

        default_active = _normalize_name(start_node.assistant.name)

        # Build assistant subgraphs and compose swarm
        assistants_ctx = create_assistant_graphs(
            user_id,
            session,
            resource_manager,
            self.assistant_factory,
            workflow,
            llm,
            self._log,
        )
        assistants = await stack.enter_async_context(assistants_ctx)

        swarm = create_swarm(
            agents=list(assistants.values()),
            state_schema=MainState,
            default_active_agent=default_active,
            context_schema=dict,
        )
        compiled_swarm = swarm.compile()
        safe_swarm = get_safe_swarm(compiled_swarm, self._log)

        outer = StateGraph(MainState)
        outer.add_node("swarm", safe_swarm)
        outer.add_edge(START, "swarm")
        outer.add_edge("swarm", END)

        compiled_graph = outer.compile(checkpointer)
        compiled_graph.name = "agent"

        return GraphArtifact(
            workflow_id=workflow.id,
            graph=compiled_graph,
            stack=stack,
            checkpointer=checkpointer,
            default_active_agent=default_active,
        )


# ==============================================================================
# Small helpers
# ==============================================================================


def _get_start_node(workflow: Workflow) -> WorkflowNode | None:
    for n in workflow.nodes:
        if n.is_start_node:
            return n
    return None
