"""
Workflow Manager for handling workflow configurations.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from dingent.core.types import Workflow, WorkflowCreate, WorkflowNode, WorkflowUpdate
from dingent.core.utils import find_project_root


class WorkflowManager:
    """Manages workflow configurations and storage."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize the workflow manager.

        Args:
            config_dir: Directory where workflow configs are stored.
                       Defaults to {project_root}/config/workflows
        """
        self.project_root = find_project_root()
        assert self.project_root
        self.config_dir = config_dir or self.project_root / "config" / "workflows"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._workflows: dict[str, Workflow] = {}
        self._load_workflows()

    def _get_workflow_file_path(self, workflow_id: str) -> Path:
        """Get the file path for a workflow configuration."""
        return self.config_dir / f"{workflow_id}.json"

    def _load_workflows(self) -> None:
        """Load all workflows from the config directory."""
        self._workflows.clear()

        if not self.config_dir.exists():
            return

        for file_path in self.config_dir.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    workflow_data = json.load(f)
                    workflow = Workflow(**workflow_data)
                    self._workflows[workflow.id] = workflow
            except Exception as e:
                print(f"Warning: Failed to load workflow from {file_path}: {e}")

    def _save_workflow_to_file(self, workflow: Workflow) -> None:
        """Save a workflow to a JSON file."""
        file_path = self._get_workflow_file_path(workflow.id)
        workflow_dict = workflow.model_dump()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(workflow_dict, f, indent=2, ensure_ascii=False)

    def _delete_workflow_file(self, workflow_id: str) -> None:
        """Delete a workflow file."""
        file_path = self._get_workflow_file_path(workflow_id)
        if file_path.exists():
            file_path.unlink()

    def get_workflows(self) -> list[Workflow]:
        """Get all workflows."""
        return list(self._workflows.values())

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a specific workflow by ID."""
        return self._workflows.get(workflow_id)

    def create_workflow(self, workflow_create: WorkflowCreate) -> Workflow:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        start_node_id = str(uuid.uuid4())
        start_node = WorkflowNode(id=start_node_id, type="start", position={"x": 0, "y": 0}, data={"assistantId": "", "assistantName": "Start", "description": "Start Node"})

        workflow = Workflow(id=workflow_id, name=workflow_create.name, description=workflow_create.description, nodes=[start_node], edges=[], created_at=now, updated_at=now)

        self._workflows[workflow_id] = workflow
        self._save_workflow_to_file(workflow)
        return workflow

    def update_workflow(self, workflow_id: str, workflow_update: WorkflowUpdate) -> Workflow | None:
        """Update an existing workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        # Update fields
        update_data = workflow_update.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.now().isoformat()

            for field, value in update_data.items():
                setattr(workflow, field, value)

            self._save_workflow_to_file(workflow)

        return workflow

    def save_workflow(self, workflow: Workflow) -> Workflow:
        """Save a complete workflow."""
        workflow.updated_at = datetime.now().isoformat()
        self._workflows[workflow.id] = workflow
        self._save_workflow_to_file(workflow)
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id not in self._workflows:
            return False

        del self._workflows[workflow_id]
        self._delete_workflow_file(workflow_id)
        return True

    def reload_workflows(self) -> None:
        """Reload all workflows from disk."""
        self._load_workflows()


# Global workflow manager instance
_workflow_manager: WorkflowManager | None = None


def get_workflow_manager() -> WorkflowManager:
    """Get the global workflow manager instance."""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager
