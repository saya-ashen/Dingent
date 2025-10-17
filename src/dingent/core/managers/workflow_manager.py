from __future__ import annotations

from threading import RLock
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from dingent.core.db.crud import workflow as crud_workflow
from dingent.core.db.models import Assistant, Workflow
from dingent.core.runtime.assistant import AssistantRuntime
from dingent.core.schemas import WorkflowCreate, WorkflowUpdate


class WorkflowManager:
    """
    Manages workflow persistence (CRUD) + active workflow selection + (optional) runtime assistant instantiation.

    Responsibilities:
      - Load all workflow JSON definitions from config/workflows
      - CRUD operations on workflows
      - Track / persist current active workflow id via ConfigManager
      - Provide runtime assistant instantiation helper (optional)
      - Emit change events to registered callbacks for observability
    """

    def __init__(
        self,
        log_manager,
        assistant_manager: AssistantRuntimeManager | None = None,
    ):
        self.assistant_manager = assistant_manager  # may be None if only doing CRUD
        self.log_manager = log_manager
        self._lock = RLock()

    def list_workflows(self, *, user_id: UUID, session: Session):
        """Lists all workflows for the current user."""
        return crud_workflow.list_workflows_by_user(session, user_id=user_id)

    def get_workflow(self, workflow_id: UUID) -> Workflow | None:
        """Retrieves a single workflow by its ID."""
        return crud_workflow.get_workflow(self.session, workflow_id=workflow_id, user_id=self.user_id)

    def create_workflow(self, wf_create: WorkflowCreate) -> Workflow:
        """
        Business logic for creating a workflow.
        1. Check for name collisions.
        2. Call CRUD layer to create the record.
        3. Emit a change event.
        """
        # Business Rule: Workflow names must be unique for a user.
        if crud_workflow.get_workflow_by_name(self.session, name=wf_create.name, user_id=self.user_id):
            raise ValueError(f"Workflow name '{wf_create.name}' already exists.")

        # Action: Create the workflow via CRUD layer
        new_workflow = crud_workflow.create_workflow(self.session, wf_create=wf_create, user_id=self.user_id)

        # Post-Action: Emit event
        return new_workflow

    def update_workflow(self, workflow_id: UUID, wf_update: WorkflowUpdate) -> Workflow:
        """
        Business logic for updating a workflow.
        1. Fetch the existing workflow.
        2. Check for name collisions if name is being changed.
        3. Call CRUD layer to update.
        4. Emit a change event.
        """
        db_workflow = self.get_workflow(workflow_id)
        if not db_workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found or user does not have permission.")

        # Business Rule: Check for name collision on update
        if wf_update.name and wf_update.name != db_workflow.name:
            if crud_workflow.get_workflow_by_name(self.session, name=wf_update.name, user_id=self.user_id):
                raise ValueError(f"Another workflow already uses the name '{wf_update.name}'.")

        # Action: Update via CRUD layer
        updated_workflow = crud_workflow.update_workflow(self.session, db_workflow=db_workflow, wf_update=wf_update)

        # Post-Action: Emit event
        return updated_workflow

    def delete_workflow(self, workflow_id: UUID) -> bool:
        """Business logic for deleting a workflow."""
        db_workflow = self.get_workflow(workflow_id)
        if not db_workflow:
            return False

        # Action: Delete via CRUD layer
        crud_workflow.delete_workflow(self.session, db_workflow=db_workflow)

        # Post-Action: Emit event
        return True

    # Graph Utilities
    # -----------------------------------------------------------------------
    def build_adjacency(self, workflow_id: UUID, *, include_self_loops: bool = False) -> dict[str, list[str]]:
        """
        Builds an adjacency list mapping assistant names to their destinations.
        Returns: {assistant_name: [destination_assistant_name, ...]}
        """
        with self._lock:
            statement = (
                select(Workflow)
                .where(Workflow.id == workflow_id, Workflow.user_id == self.user_id)
                .options(
                    selectinload(Workflow.nodes).selectinload("assistant"),
                    selectinload(Workflow.edges),
                )
            )  # Eagerly load all required relationships in a single query

            wf = self.session.exec(statement).first()
            if not wf:
                raise ValueError(f"Workflow '{workflow_id}' not found.")

            node_id_to_assistant_name: dict[UUID, str] = {node.id: node.assistant.name for node in wf.nodes if node.assistant}

            adjacency: dict[str, set[str]] = {aname: set() for aname in node_id_to_assistant_name.values()}

            for edge in wf.edges:
                src_a = node_id_to_assistant_name.get(edge.source_node_id)
                tgt_a = node_id_to_assistant_name.get(edge.target_node_id)
                if not src_a or not tgt_a:
                    continue

                if include_self_loops or src_a != tgt_a:
                    adjacency.setdefault(src_a, set()).add(tgt_a)

            return {k: sorted(v) for k, v in adjacency.items()}

    # -----------------------------------------------------------------------
    # Runtime Assistant Instantiation
    # -----------------------------------------------------------------------
    async def instantiate_workflow_assistants(
        self,
        workflow_id: str,
        *,
        set_active: bool = True,
        reset_assistants: bool = True,
        include_self_loops: bool = False,
        honor_bidirectional: bool = True,
        mutate_assistant_destinations: bool = True,
    ) -> dict[str, Assistant]:
        """
        Construct runtime assistant instances according to the workflow graph.

        Args:
          workflow_id: target workflow
          set_active: mark as active workflow
          reset_assistants: if True, calls assistant_manager.aclose() before building
          include_self_loops: keep A->A edges
          honor_bidirectional: expand bidirectional edges
          mutate_assistant_destinations: if True, assigns computed destinations to assistant.destinations
        """
        if not self.assistant_manager:
            raise RuntimeError("assistant_manager is not attached to WorkflowManager.")

        wf = self.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        adj = self.build_adjacency(
            workflow_id,
            include_self_loops=include_self_loops,
            honor_bidirectional=honor_bidirectional,
        )

        if reset_assistants:
            await self.assistant_manager.aclose()

        # Build mapping assistantName -> assistantId from workflow nodes
        assistant_name_to_id: dict[str, str] = {}
        for node in wf.nodes:
            assistant_name_to_id[str(node.id)] = str(node.assistant_id)

        result: dict[str, AssistantRuntime] = {}
        for aname, aid in assistant_name_to_id.items():
            try:
                assistant = await self.assistant_manager.get_runtime_assistant(aid)
            except ValueError as e:
                self.log_manager.log_with_context(
                    "error",
                    message="Failed to instantiate assistant for workflow: {assistant_id}",
                    context={"assistant_id": aid, "assistant_name": aname, "error": str(e)},
                )
                continue
            if mutate_assistant_destinations:
                assistant.destinations = adj.get(aname, [])
            result[aname] = assistant

        return result
