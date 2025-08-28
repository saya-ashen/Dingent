#!/usr/bin/env python3
"""
Test for workflow cleanup when assistants are deleted.

This test verifies that when an assistant is deleted, any workflow nodes
that reference that assistant are automatically removed, along with their
connected edges.
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from dingent.core.config_manager import ConfigManager
from dingent.core.settings import AppSettings
from dingent.core.types import AssistantCreate, WorkflowCreate, WorkflowEdge, WorkflowEdgeData, WorkflowNode, WorkflowNodeData
from dingent.core.workflow_manager import WorkflowManager


def test_workflow_cleanup_on_assistant_deletion():
    """Test that workflows are properly cleaned up when an assistant is deleted."""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Initialize workflow manager with temporary config
        workflow_manager = WorkflowManager.__new__(WorkflowManager)
        workflow_manager.project_root = Path.cwd()
        workflow_manager.config_dir = temp_path / "config" / "workflows"
        workflow_manager.config_dir.mkdir(parents=True, exist_ok=True)
        workflow_manager._workflows = {}
        workflow_manager._active_workflow_id = None
        workflow_manager._load_workflows()

        # Initialize config manager with temporary config
        config_manager = ConfigManager.__new__(ConfigManager)
        config_manager.project_root = Path.cwd()
        config_manager._global_config_path = temp_path / "dingent.toml"
        config_manager._config_root = temp_path / "config"
        config_manager._assistants_dir = config_manager._config_root / "assistants"
        config_manager._plugins_dir = config_manager._config_root / "plugins"
        config_manager._workflows_dir = config_manager._config_root / "workflows"
        config_manager._assistants_dir.mkdir(parents=True, exist_ok=True)
        config_manager._plugins_dir.mkdir(parents=True, exist_ok=True)

        # Load initial empty settings
        config_manager._settings = AppSettings.model_validate(
            {
                "llm": {
                    "model": "placeholder-model",
                    "provider": None,
                    "base_url": None,
                    "api_key": None,
                },
                "assistants": [],
                "workflows": [],
            }
        )

        # Create test assistants
        assistant1 = AssistantCreate(name="assistant-1", description="First assistant")
        assistant2 = AssistantCreate(name="assistant-2", description="Second assistant")

        config_manager.add_assistant(assistant1)
        config_manager.add_assistant(assistant2)

        assistant1_settings = config_manager.get_assistant_by_name("assistant-1")
        assistant2_settings = config_manager.get_assistant_by_name("assistant-2")

        assistant1_id = assistant1_settings.id
        assistant2_id = assistant2_settings.id

        # Create a workflow with both assistants
        workflow = workflow_manager.create_workflow(WorkflowCreate(name="test-workflow", description="Test workflow"))

        node1_id = str(uuid.uuid4())
        node2_id = str(uuid.uuid4())

        node1 = WorkflowNode(
            id=node1_id, type="assistant", position={"x": 100, "y": 100}, data=WorkflowNodeData(assistantId=assistant1_id, assistantName=assistant1.name, isStart=True)
        )

        node2 = WorkflowNode(
            id=node2_id, type="assistant", position={"x": 300, "y": 100}, data=WorkflowNodeData(assistantId=assistant2_id, assistantName=assistant2.name, isStart=False)
        )

        edge = WorkflowEdge(id=str(uuid.uuid4()), source=node1_id, target=node2_id, data=WorkflowEdgeData(mode="single"))

        workflow.nodes = [node1, node2]
        workflow.edges = [edge]
        workflow_manager.save_workflow(workflow)

        # Verify initial state
        assert len(workflow.nodes) == 2
        assert len(workflow.edges) == 1

        # Delete assistant1 and trigger cleanup
        modified_workflows = workflow_manager.cleanup_workflows_for_deleted_assistant(assistant1_id)

        # Verify cleanup results
        assert len(modified_workflows) == 1
        assert workflow.id in modified_workflows

        # Reload workflow to check changes
        updated_workflow = workflow_manager.get_workflow(workflow.id)

        # Should have 1 node (assistant2 only) and 0 edges
        assert len(updated_workflow.nodes) == 1
        assert len(updated_workflow.edges) == 0

        # Remaining node should reference assistant2
        remaining_node = updated_workflow.nodes[0]
        assert remaining_node.data.assistantId == assistant2_id

        # No nodes should reference the deleted assistant
        deleted_refs = [node for node in updated_workflow.nodes if node.data.assistantId == assistant1_id]
        assert len(deleted_refs) == 0


def test_workflow_cleanup_multiple_workflows():
    """Test cleanup across multiple workflows."""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Setup managers
        workflow_manager = WorkflowManager.__new__(WorkflowManager)
        workflow_manager.project_root = Path.cwd()
        workflow_manager.config_dir = temp_path / "config" / "workflows"
        workflow_manager.config_dir.mkdir(parents=True, exist_ok=True)
        workflow_manager._workflows = {}
        workflow_manager._active_workflow_id = None
        workflow_manager._load_workflows()

        config_manager = ConfigManager.__new__(ConfigManager)
        config_manager.project_root = Path.cwd()
        config_manager._global_config_path = temp_path / "dingent.toml"
        config_manager._config_root = temp_path / "config"
        config_manager._assistants_dir = config_manager._config_root / "assistants"
        config_manager._plugins_dir = config_manager._config_root / "plugins"
        config_manager._workflows_dir = config_manager._config_root / "workflows"
        config_manager._assistants_dir.mkdir(parents=True, exist_ok=True)
        config_manager._plugins_dir.mkdir(parents=True, exist_ok=True)

        config_manager._settings = AppSettings.model_validate(
            {
                "llm": {"model": "placeholder-model", "provider": None, "base_url": None, "api_key": None},
                "assistants": [],
                "workflows": [],
            }
        )

        # Create assistants
        assistant1 = AssistantCreate(name="shared-assistant", description="Shared assistant")
        assistant2 = AssistantCreate(name="unique-assistant", description="Unique assistant")

        config_manager.add_assistant(assistant1)
        config_manager.add_assistant(assistant2)

        shared_id = config_manager.get_assistant_by_name("shared-assistant").id
        unique_id = config_manager.get_assistant_by_name("unique-assistant").id

        # Create two workflows, both using the shared assistant
        workflow1 = workflow_manager.create_workflow(WorkflowCreate(name="workflow-1", description="First workflow"))
        workflow2 = workflow_manager.create_workflow(WorkflowCreate(name="workflow-2", description="Second workflow"))

        # Workflow 1: shared + unique assistants
        workflow1.nodes = [
            WorkflowNode(
                id=str(uuid.uuid4()), type="assistant", position={"x": 100, "y": 100}, data=WorkflowNodeData(assistantId=shared_id, assistantName="shared-assistant", isStart=True)
            ),
            WorkflowNode(
                id=str(uuid.uuid4()), type="assistant", position={"x": 300, "y": 100}, data=WorkflowNodeData(assistantId=unique_id, assistantName="unique-assistant", isStart=False)
            ),
        ]

        # Workflow 2: only shared assistant
        workflow2.nodes = [
            WorkflowNode(
                id=str(uuid.uuid4()), type="assistant", position={"x": 200, "y": 200}, data=WorkflowNodeData(assistantId=shared_id, assistantName="shared-assistant", isStart=True)
            )
        ]

        workflow_manager.save_workflow(workflow1)
        workflow_manager.save_workflow(workflow2)

        # Delete the shared assistant
        modified_workflows = workflow_manager.cleanup_workflows_for_deleted_assistant(shared_id)

        # Both workflows should be modified
        assert len(modified_workflows) == 2
        assert workflow1.id in modified_workflows
        assert workflow2.id in modified_workflows

        # Verify results
        updated_workflow1 = workflow_manager.get_workflow(workflow1.id)
        updated_workflow2 = workflow_manager.get_workflow(workflow2.id)

        # Workflow 1 should have 1 node (unique assistant only)
        assert len(updated_workflow1.nodes) == 1
        assert updated_workflow1.nodes[0].data.assistantId == unique_id

        # Workflow 2 should have 0 nodes (only had shared assistant)
        assert len(updated_workflow2.nodes) == 0


if __name__ == "__main__":
    test_workflow_cleanup_on_assistant_deletion()
    test_workflow_cleanup_multiple_workflows()
    print("✅ All tests passed!")
