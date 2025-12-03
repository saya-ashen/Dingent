from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, select

from dingent.core.db.models import Workflow, WorkflowEdge, WorkflowNode
from dingent.core.schemas import (
    WorkflowCreate,
    WorkflowEdgeCreate,
    WorkflowEdgeUpdate,
    WorkflowNodeCreate,
    WorkflowNodeUpdate,
    WorkflowReplace,
    WorkflowUpdate,
)

# --- Workflow CRUD ---


def get_workflow(db: Session, workflow_id: UUID, user_id: UUID) -> Workflow | None:
    """
    Get a single workflow by ID, ensuring it belongs to the specified user.
    """
    statement = select(Workflow).where(
        Workflow.id == workflow_id,
        Workflow.user_id == user_id,
    )
    return db.exec(statement).first()


def get_workflow_by_name(db: Session, name: str, user_id: UUID) -> Workflow | None:
    """
    Get a single workflow by name for a specific user.
    """
    statement = select(Workflow).where(
        Workflow.name == name,
        Workflow.user_id == user_id,
    )
    return db.exec(statement).first()


def replace_workflow(db: Session, db_workflow: Workflow, wf_create: WorkflowReplace) -> Workflow:
    """
    Replaces an existing workflow with new data, including its nodes and edges.

    This is an atomic operation: it deletes all existing nodes and edges
    for the workflow and creates new ones from the `wf_create` payload.
    """
    # 1. Delete all existing edges and nodes associated with the workflow
    # It's good practice to delete edges first to avoid foreign key constraint issues.
    for edge in list_workflow_edges(db, db_workflow.id):
        db.delete(edge)
    for node in list_workflow_nodes(db, db_workflow.id):
        db.delete(node)

    db.flush()

    # 2. Update the workflow's own properties (name, description, etc.)
    # We exclude nodes and edges as we will handle them separately.
    update_data = wf_create.model_dump(exclude={"nodes", "edges"})
    for key, value in update_data.items():
        setattr(db_workflow, key, value)
    db.add(db_workflow)

    db.flush()
    # 3. Create new nodes from the payload
    # Assumes that wf_create.nodes contains a list of WorkflowNodeCreate schemas
    # and that the IDs in the payload are the ones we want to use.
    id_map: dict[str, UUID] = {}
    if wf_create.nodes:
        for node_create in wf_create.nodes:
            client_id_str = str(node_create.id) if getattr(node_create, "id", None) is not None else None

            # 丢弃前端 id，用 DB/模型默认 UUID
            new_node = WorkflowNode.model_validate(
                node_create.model_dump(exclude={"id"}),
                update={"workflow_id": db_workflow.id},
            )
            db.add(new_node)
            if client_id_str:
                id_map[client_id_str] = new_node.id

    db.flush()

    # 4. Create new edges from the payload
    # Assumes that wf_create.edges contains a list of WorkflowEdgeCreate schemas
    def resolve_node_id(raw) -> UUID:
        raw_str = str(raw)
        if raw_str in id_map:
            return id_map[raw_str]
        try:
            return UUID(raw_str)
        except ValueError:
            raise ValueError(f"edge 引用的节点 id 未找到映射且不是合法 UUID: {raw_str}")

    if wf_create.edges:
        for edge_create in wf_create.edges:
            src = resolve_node_id(edge_create.source_node_id)
            tgt = resolve_node_id(edge_create.target_node_id)

            new_edge = WorkflowEdge.model_validate(
                edge_create.model_dump(exclude={"id"}),
                update={
                    "workflow_id": db_workflow.id,
                    "source_node_id": src,
                    "target_node_id": tgt,
                },
            )
            db.add(new_edge)

    db.flush()
    # 5. Commit the transaction and refresh the state
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


def list_workflows_by_user(db: Session, user_id: UUID) -> list[Workflow]:
    """
    List all workflows for a specific user.
    """
    statement = select(Workflow).where(Workflow.user_id == user_id)
    return db.exec(statement).all()


def create_workflow(db: Session, wf_create: WorkflowCreate, user_id: UUID) -> Workflow:
    """
    Create a new workflow record in the database.
    """
    db_workflow = Workflow.model_validate(wf_create, update={"user_id": user_id})
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


def update_workflow(db: Session, db_workflow: Workflow, wf_update: WorkflowUpdate) -> Workflow:
    """
    Update an existing workflow record.
    """
    update_data = wf_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_workflow, key, value)
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow


def delete_workflow(db: Session, db_workflow: Workflow) -> None:
    """
    Delete a workflow record from the database.
    """
    db.delete(db_workflow)
    db.commit()


# --- Node CRUD ---


def list_workflow_nodes(db: Session, workflow_id: UUID) -> Sequence[WorkflowNode]:
    statement = select(WorkflowNode).where(WorkflowNode.workflow_id == workflow_id)
    return db.exec(statement).all()


def create_workflow_node(db: Session, workflow_id: UUID, node_in: WorkflowNodeCreate) -> WorkflowNode:
    db_node = WorkflowNode.model_validate(node_in.model_dump(exclude={"id"}), update={"workflow_id": workflow_id})
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node


def get_workflow_node(db: Session, workflow_id: UUID, node_id: UUID) -> WorkflowNode | None:
    statement = select(WorkflowNode).where(
        WorkflowNode.id == node_id,
        WorkflowNode.workflow_id == workflow_id,
    )
    return db.exec(statement).first()


def update_workflow_node(
    db: Session,
    workflow_id: UUID,
    node_id: UUID,
    node_update: WorkflowNodeUpdate,
) -> WorkflowNode:
    db_node = get_workflow_node(db, workflow_id, node_id)
    if not db_node:
        raise ValueError("Node not found or does not belong to the workflow")

    update_data = node_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_node, key, value)

    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node


def delete_workflow_node(db: Session, workflow_id: UUID, node_id: UUID) -> None:
    db_node = get_workflow_node(db, workflow_id, node_id)
    if not db_node:
        raise ValueError("Node not found or does not belong to the workflow")
    db.delete(db_node)
    db.commit()


# --- Edge CRUD ---


def list_workflow_edges(db: Session, workflow_id: UUID) -> Sequence[WorkflowEdge]:
    statement = select(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow_id)
    return db.exec(statement).all()


def get_workflow_edge(db: Session, workflow_id: UUID, edge_id: UUID) -> WorkflowEdge | None:
    statement = select(WorkflowEdge).where(
        WorkflowEdge.id == edge_id,
        WorkflowEdge.workflow_id == workflow_id,
    )
    return db.exec(statement).first()


def _ensure_node_in_workflow(db: Session, workflow_id: UUID, node_id: UUID) -> None:
    node = get_workflow_node(db, workflow_id, node_id)
    if not node:
        raise ValueError(f"Node {node_id} not found in workflow {workflow_id}")


def create_workflow_edge(
    db: Session,
    workflow_id: UUID,
    edge_in: WorkflowEdgeCreate,
) -> WorkflowEdge:
    """
    Create an edge; validates that both endpoint nodes exist and belong to the workflow.
    """
    data = edge_in.model_dump()
    from_id: UUID = data.get("from_node_id")
    to_id: UUID = data.get("to_node_id")

    # Validate endpoints
    _ensure_node_in_workflow(db, workflow_id, from_id)
    _ensure_node_in_workflow(db, workflow_id, to_id)

    db_edge = WorkflowEdge.model_validate(edge_in, update={"workflow_id": workflow_id})
    db.add(db_edge)
    db.commit()
    db.refresh(db_edge)
    return db_edge


def update_workflow_edge(
    db: Session,
    workflow_id: UUID,
    edge_id: UUID,
    edge_update: WorkflowEdgeUpdate,
) -> WorkflowEdge:
    db_edge = get_workflow_edge(db, workflow_id, edge_id)
    if not db_edge:
        raise ValueError("Edge not found or does not belong to the workflow")

    update_data = edge_update.model_dump(exclude_unset=True)

    # If endpoints are being changed, validate them
    if "from_node_id" in update_data:
        _ensure_node_in_workflow(db, workflow_id, update_data["from_node_id"])
    if "to_node_id" in update_data:
        _ensure_node_in_workflow(db, workflow_id, update_data["to_node_id"])

    for key, value in update_data.items():
        setattr(db_edge, key, value)

    db.add(db_edge)
    db.commit()
    db.refresh(db_edge)
    return db_edge


def delete_workflow_edge(db: Session, workflow_id: UUID, edge_id: UUID) -> None:
    db_edge = get_workflow_edge(db, workflow_id, edge_id)
    if not db_edge:
        raise ValueError("Edge not found or does not belong to the workflow")
    db.delete(db_edge)
    db.commit()
