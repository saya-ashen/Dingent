from uuid import UUID
from typing import List, Optional

from sqlmodel import Session, select

from dingent.core.db.models import Workflow, WorkflowNode, WorkflowEdge
from dingent.core.types import WorkflowCreate, WorkflowUpdate  # Assuming these exist

# --- Workflow CRUD ---


def get_workflow(db: Session, workflow_id: UUID, user_id: UUID) -> Optional[Workflow]:
    """
    Get a single workflow by ID, ensuring it belongs to the specified user.
    """
    statement = select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == user_id)
    return db.exec(statement).first()


def get_workflow_by_name(db: Session, name: str, user_id: UUID) -> Optional[Workflow]:
    """
    Get a single workflow by name for a specific user.
    """
    statement = select(Workflow).where(Workflow.name == name, Workflow.user_id == user_id)
    return db.exec(statement).first()


def list_workflows_by_user(db: Session, user_id: UUID):
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


# --- You can add CRUD for Nodes and Edges as needed ---
# For example:
def create_workflow_node(db: Session, node_data: dict) -> WorkflowNode:
    db_node = WorkflowNode(**node_data)
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node
