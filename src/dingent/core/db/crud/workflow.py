from uuid import UUID
from typing import Optional, Sequence

from sqlmodel import Session, select

from dingent.core.db.models import Workflow, WorkflowNode, WorkflowEdge
from dingent.core.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowNodeCreate,
    WorkflowNodeUpdate,
    WorkflowEdgeCreate,
    WorkflowEdgeUpdate,
)

# --- Workflow CRUD ---


def get_workflow(db: Session, workflow_id: UUID, user_id: UUID) -> Optional[Workflow]:
    """
    Get a single workflow by ID, ensuring it belongs to the specified user.
    """
    statement = select(Workflow).where(
        Workflow.id == workflow_id,
        Workflow.user_id == user_id,
    )
    return db.exec(statement).first()


def get_workflow_by_name(db: Session, name: str, user_id: UUID) -> Optional[Workflow]:
    """
    Get a single workflow by name for a specific user.
    """
    statement = select(Workflow).where(
        Workflow.name == name,
        Workflow.user_id == user_id,
    )
    return db.exec(statement).first()


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
    db_node = WorkflowNode.model_validate(node_in, update={"workflow_id": workflow_id})
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
