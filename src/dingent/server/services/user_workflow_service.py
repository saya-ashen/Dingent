from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, SQLModel, select

from dingent.core.db.crud import workflow as crud_workflow
from dingent.core.db.models import Workflow, WorkflowNode

# --- New dependencies provided by user ---
from dingent.core.runtime.assistant import AssistantRuntime
from dingent.core.schemas import WorkflowCreate, WorkflowEdgeRead, WorkflowNodeCreate, WorkflowNodeRead, WorkflowRead, WorkflowReadBasic, WorkflowReplace, WorkflowUpdate
from dingent.server.services.user_assistant_service import UserAssistantService


class WorkflowNotFoundError(ValueError):
    pass


class WorkflowAlreadyRunningError(RuntimeError):
    pass


class AssistantServiceUnavailableError(RuntimeError):
    pass


class WorkflowRunStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass
class WorkflowRun:
    user_id: UUID
    workflow_id: UUID
    status: WorkflowRunStatus = WorkflowRunStatus.IDLE
    message: str | None = None
    assistants: dict[str, AssistantRuntime] = field(default_factory=dict)  # assistant_name -> runtime


class WorkflowRunRead(SQLModel):
    workflow_id: UUID
    status: str
    message: str | None = None


class UserWorkflowService:
    """
    Request-scoped service that manages the lifecycle of a user's *workflow run* and
    wires Assistant runtimes using the provided `UserAssistantService`.

    Responsibilities
    --------------
    - Create/read/update/delete workflows (optional helpers)
    - Start/stop workflows for a user
    - Build adjacency from workflow graph and assign destinations to runtimes
    - Track in-memory run state per (user_id, workflow_id)
    - **CRUD for nodes & edges** within a workflow

    Notes
    -----
    - This service assumes per-request construction with a live `Session` and a
      `UserAssistantService` that is already scoped to the same user & session.
    - All assistant runtime creation is **async**, so `start_workflow` and other
      APIs that touch runtimes are async as well.
    """

    def __init__(
        self,
        *,
        user_id: UUID,
        session: Session,
        assistant_service: UserAssistantService | None,
        log_manager,
    ) -> None:
        self.user_id = user_id
        self.session = session
        self.assistant_service = assistant_service
        self._log = log_manager

        # Track runs in-memory (per-process). Key: (user_id, workflow_id)
        self._runs: dict[tuple[UUID, UUID], WorkflowRun] = {}
        self._lock = RLock()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def start_workflow(
        self,
        workflow: WorkflowCreate | UUID,
        *,
        include_self_loops: bool = False,
        honor_bidirectional: bool = True,
        reset_existing: bool = True,
        mutate_assistant_destinations: bool = True,
    ) -> WorkflowRun:
        """
        Start (or create & start) a workflow for `self.user_id`.

        `workflow` can be an existing `UUID` or a `WorkflowCreate` to be persisted first.
        """
        if self.assistant_service is None:
            raise AssistantServiceUnavailableError("assistant_service is required to start workflows")

        # Resolve or create the workflow
        if isinstance(workflow, UUID):
            wf = self._get_workflow(workflow)
            if wf is None:
                raise WorkflowNotFoundError(f"Workflow '{workflow}' not found or access denied.")
        else:
            # unique name per user
            if crud_workflow.get_workflow_by_name(self.session, name=workflow.name, user_id=self.user_id):
                raise ValueError(f"Workflow name '{workflow.name}' already exists.")
            wf = crud_workflow.create_workflow(self.session, wf_create=workflow, user_id=self.user_id)

        key = (self.user_id, wf.id)
        with self._lock:
            if key in self._runs and self._runs[key].status == WorkflowRunStatus.RUNNING:
                raise WorkflowAlreadyRunningError(f"Workflow '{wf.id}' is already running for user '{self.user_id}'.")
            self._runs[key] = WorkflowRun(user_id=self.user_id, workflow_id=wf.id)

        # Fresh load for graph relationships
        wf = self._get_workflow(wf.id, eager=True)
        assert wf is not None

        # Compute adjacency and build runtimes
        try:
            adjacency = self._build_adjacency(
                wf,
                include_self_loops=include_self_loops,
                honor_bidirectional=honor_bidirectional,
            )

            # Optionally clear existing runtimes (request-scoped caches live only per request,
            # so typically there is nothing to reset across requests; kept for parity/semantics)
            if reset_existing:
                pass  # no-op by default since UserAssistantService is request-scoped

            name_to_id: dict[str, UUID] = {}
            for node in wf.nodes:
                if node.assistant:
                    name_to_id[node.assistant.name] = node.assistant_id

            runtimes: dict[str, AssistantRuntime] = {}
            for a_name, a_id in name_to_id.items():
                try:
                    runtime = await self.assistant_service.get_runtime_assistant(a_id)
                    if mutate_assistant_destinations:
                        # destinations use assistant names
                        runtime.destinations = adjacency.get(a_name, [])
                    runtimes[a_name] = runtime
                except Exception as e:
                    self._log.log_with_context(
                        "error",
                        message="Failed to create runtime for assistant",
                        context={"assistant_id": str(a_id), "assistant_name": a_name, "error": str(e)},
                    )
                    # continue; partial graph may still be useful

            with self._lock:
                run = self._runs[key]
                run.status = WorkflowRunStatus.RUNNING
                run.message = None
                run.assistants = runtimes
                return run

        except Exception as e:
            with self._lock:
                run = self._runs[key]
                run.status = WorkflowRunStatus.FAILED
                run.message = str(e)
            self._log.log_with_context(
                "error",
                message="Failed to start workflow",
                context={"user_id": str(self.user_id), "workflow_id": str(wf.id), "error": str(e)},
            )
            raise

    def get_workflow_status(self, workflow_id: UUID) -> WorkflowRun:
        key = (self.user_id, workflow_id)
        with self._lock:
            run = self._runs.get(key)
            if run is not None:
                return run

        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")

        idle = WorkflowRun(user_id=self.user_id, workflow_id=workflow_id, status=WorkflowRunStatus.STOPPED)
        with self._lock:
            self._runs[key] = idle
        return idle

    async def stop_workflow(self, workflow_id: UUID) -> WorkflowRun:
        key = (self.user_id, workflow_id)
        with self._lock:
            existing = self._runs.get(key)

        # Validate workflow existence regardless of run state
        if self._get_workflow(workflow_id) is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")

        # Best-effort: clear destinations to avoid accidental message passing in other layers
        try:
            if existing and existing.assistants:
                for rt in existing.assistants.values():
                    try:
                        rt.destinations = []
                    except Exception:
                        pass
        finally:
            with self._lock:
                updated = self._runs.get(key) or WorkflowRun(user_id=self.user_id, workflow_id=workflow_id)
                updated.status = WorkflowRunStatus.STOPPED
                updated.message = None
                updated.assistants = {}
                self._runs[key] = updated
                return updated

    # ---------------------------------------------------------------------
    # Optional CRUD passthroughs (workflows)
    # ---------------------------------------------------------------------
    def list_workflows(self, *, eager: bool = False) -> list[WorkflowReadBasic | WorkflowRead]:
        if eager:
            wfs = self.session.exec(
                select(Workflow)
                .where(Workflow.user_id == self.user_id)
                .options(
                    selectinload(Workflow.nodes).selectinload(WorkflowNode.assistant),
                    selectinload(Workflow.edges),
                )
            ).all()
            return [WorkflowRead.model_validate(wf) for wf in wfs]
        else:
            wfs = self.session.exec(select(Workflow).where(Workflow.user_id == self.user_id)).all()
            return [WorkflowReadBasic.model_validate(wf) for wf in wfs]

    def get_workflow(self, workflow_id: UUID, *, eager: bool = False) -> WorkflowRead | WorkflowReadBasic | None:
        wf = self._get_workflow(workflow_id, eager=eager)
        if wf is None:
            return None
        if eager:
            return WorkflowRead.model_validate(wf)
        else:
            return WorkflowReadBasic.model_validate(wf)

    def create_workflow(self, wf_create: WorkflowCreate) -> WorkflowReadBasic:
        if crud_workflow.get_workflow_by_name(self.session, name=wf_create.name, user_id=self.user_id):
            raise ValueError(f"Workflow name '{wf_create.name}' already exists.")
        wf = crud_workflow.create_workflow(self.session, wf_create=wf_create, user_id=self.user_id)
        return WorkflowReadBasic.model_validate(wf)

    def replace_workflow(self, workflow_id: UUID, wf_create: WorkflowReplace):
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")

        if wf_create.name != wf.name:
            if crud_workflow.get_workflow_by_name(self.session, name=wf_create.name, user_id=self.user_id):
                raise ValueError(f"Another workflow already uses the name '{wf_create.name}'.")

        crud_workflow.replace_workflow(self.session, db_workflow=wf, wf_create=wf_create)

    def update_workflow(self, workflow_id: UUID, wf_update: WorkflowUpdate) -> WorkflowReadBasic:
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")

        if wf_update.name and wf_update.name != wf.name:
            if crud_workflow.get_workflow_by_name(self.session, name=wf_update.name, user_id=self.user_id):
                raise ValueError(f"Another workflow already uses the name '{wf_update.name}'.")

        updated = crud_workflow.update_workflow(self.session, db_workflow=wf, wf_update=wf_update)
        return WorkflowReadBasic.model_validate(updated)

    def delete_workflow(self, workflow_id: UUID) -> bool:
        wf = self._get_workflow(workflow_id)
        if wf is None:
            return False
        crud_workflow.delete_workflow(self.session, db_workflow=wf)
        # Also mark stopped in registry
        key = (self.user_id, workflow_id)
        with self._lock:
            self._runs[key] = WorkflowRun(user_id=self.user_id, workflow_id=workflow_id, status=WorkflowRunStatus.STOPPED)
        return True

    # ---------------------------------------------------------------------
    # Nodes CRUD
    # ---------------------------------------------------------------------
    def list_nodes(self, workflow_id: UUID):
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")
        crud_workflow.list_workflow_nodes(self.session, workflow_id=workflow_id)
        node_reads = [WorkflowNodeRead.model_validate(node) for node in wf.nodes]
        return node_reads

    def create_node(self, workflow_id: UUID, payload: WorkflowNodeCreate):  # payload: WorkflowNodeCreate
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")
        node = crud_workflow.create_workflow_node(self.session, workflow_id=workflow_id, node_in=payload)
        return WorkflowNodeRead.model_validate(node)

    def update_node(self, workflow_id: UUID, node_id: UUID, payload):  # payload: WorkflowNodeUpdate
        node = crud_workflow.update_workflow_node(self.session, workflow_id=workflow_id, node_id=node_id, node_update=payload)
        return WorkflowNodeRead.model_validate(node)

    def delete_node(self, workflow_id: UUID, node_id: UUID) -> bool:
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")
        db_node = crud_workflow.get_workflow_node(self.session, workflow_id=workflow_id, node_id=node_id)
        if not db_node or db_node.workflow_id != workflow_id:
            return False
        crud_workflow.delete_workflow_node(self.session, workflow_id=workflow_id, node_id=node_id)
        return True

    # ---------------------------------------------------------------------
    # Edges CRUD
    # ---------------------------------------------------------------------
    def list_edges(self, workflow_id: UUID):
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")
        edges = crud_workflow.list_workflow_edges(self.session, workflow_id=workflow_id)
        edge_reads = [WorkflowEdgeRead.model_validate(edge) for edge in edges]
        return edge_reads

    def create_edge(self, workflow_id: UUID, payload):  # payload: WorkflowEdgeCreate
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")
        edge = crud_workflow.create_workflow_edge(self.session, workflow_id=workflow_id, edge_in=payload)
        return WorkflowEdgeRead.model_validate(edge)

    def update_edge(self, workflow_id: UUID, edge_id: UUID, payload):  # payload: WorkflowEdgeUpdate
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")
        db_edge = crud_workflow.get_workflow_edge(self.session, workflow_id=workflow_id, edge_id=edge_id)
        if not db_edge or db_edge.workflow_id != workflow_id:
            raise HTTPException(status_code=404, detail="Edge not found")
        edge = crud_workflow.update_workflow_edge(self.session, workflow_id=workflow_id, edge_id=edge_id, edge_update=payload)
        return WorkflowEdgeRead.model_validate(edge)

    def delete_edge(self, workflow_id: UUID, edge_id: UUID) -> bool:
        wf = self._get_workflow(workflow_id)
        if wf is None:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' not found or access denied.")
        db_edge = crud_workflow.get_workflow_edge(self.session, workflow_id=workflow_id, edge_id=edge_id)
        if not db_edge or db_edge.workflow_id != workflow_id:
            return False
        crud_workflow.delete_workflow_edge(self.session, workflow_id=workflow_id, edge_id=edge_id)
        return True

    # ---------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------
    def _get_workflow(self, workflow_id: UUID, *, eager: bool = False) -> Workflow | None:
        stmt = select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == self.user_id)
        if eager:
            stmt = stmt.options(
                selectinload(Workflow.nodes).selectinload(WorkflowNode.assistant),
                selectinload(Workflow.edges),
            )
        return self.session.exec(stmt).first()

    @staticmethod
    def _build_adjacency(
        wf: Workflow,
        *,
        include_self_loops: bool,
        honor_bidirectional: bool,
    ) -> dict[str, list[str]]:
        """assistant_name -> sorted(list(destination_assistant_names))"""
        node_id_to_name: dict[UUID, str] = {node.id: node.assistant.name for node in wf.nodes if getattr(node, "assistant", None)}
        adj: dict[str, set[str]] = {name: set() for name in node_id_to_name.values()}

        for edge in wf.edges:
            src = node_id_to_name.get(edge.source_node_id)
            tgt = node_id_to_name.get(edge.target_node_id)
            if not src or not tgt:
                continue

            if include_self_loops or src != tgt:
                adj.setdefault(src, set()).add(tgt)

            if honor_bidirectional and bool(getattr(edge, "bidirectional", False)):
                if include_self_loops or src != tgt:
                    adj.setdefault(tgt, set()).add(src)

        return {k: sorted(v) for k, v in adj.items()}
