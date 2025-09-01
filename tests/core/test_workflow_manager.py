"""
Tests for WorkflowManager - workflow CRUD, active workflow management, and cleanup.
"""
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dingent.core.types import (
    Workflow, 
    WorkflowCreate, 
    WorkflowUpdate,
    WorkflowNode,
    WorkflowNodeData,
    WorkflowEdge,
    WorkflowEdgeData
)
from dingent.core.workflow_manager import WorkflowManager


class TestWorkflowManager:
    """Test suite for WorkflowManager."""

    @pytest.fixture
    def workflow_manager(self, mock_config_manager, mock_log_manager, temp_project_root):
        """Create a WorkflowManager instance for testing."""
        return WorkflowManager(
            config_manager=mock_config_manager,
            log_manager=mock_log_manager,
            workflows_dir=temp_project_root / "config" / "workflows",
            auto_set_active_if_missing=False
        )

    def test_workflow_manager_initialization(self, workflow_manager, temp_project_root):
        """Test WorkflowManager initializes correctly."""
        assert workflow_manager._dir == temp_project_root / "config" / "workflows"
        assert workflow_manager._workflows == {}
        assert workflow_manager._active_workflow_id is None
        assert workflow_manager._callbacks == []

    def test_list_workflows_empty_initially(self, workflow_manager):
        """Test list_workflows returns empty list initially."""
        workflows = workflow_manager.list_workflows()
        assert workflows == []

    def test_create_workflow_basic(self, workflow_manager, sample_workflow_create):
        """Test create_workflow creates new workflow."""
        workflow = workflow_manager.create_workflow(sample_workflow_create)
        
        assert isinstance(workflow, Workflow)
        assert workflow.name == sample_workflow_create.name
        assert workflow.description == sample_workflow_create.description
        assert workflow.id is not None
        assert len(workflow.id) > 0
        assert workflow.nodes == []
        assert workflow.edges == []

    def test_create_workflow_saves_to_disk(self, workflow_manager, sample_workflow_create, temp_project_root):
        """Test create_workflow saves workflow file to disk."""
        workflow = workflow_manager.create_workflow(sample_workflow_create)
        
        workflow_file = temp_project_root / "config" / "workflows" / f"{workflow.id}.json"
        assert workflow_file.exists()

    def test_create_workflow_make_active(self, workflow_manager, sample_workflow_create):
        """Test create_workflow with make_active=True sets as active."""
        workflow = workflow_manager.create_workflow(sample_workflow_create, make_active=True)
        
        assert workflow_manager.active_workflow_id == workflow.id

    def test_get_workflow_existing(self, workflow_manager, sample_workflow_create):
        """Test get_workflow retrieves existing workflow."""
        created = workflow_manager.create_workflow(sample_workflow_create)
        retrieved = workflow_manager.get_workflow(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.description == created.description

    def test_get_workflow_nonexistent(self, workflow_manager):
        """Test get_workflow returns None for non-existent workflow."""
        result = workflow_manager.get_workflow("non-existent-id")
        assert result is None

    def test_get_workflow_id_by_name(self, workflow_manager, sample_workflow_create):
        """Test get_workflow_id_by_name finds workflow by name."""
        created = workflow_manager.create_workflow(sample_workflow_create)
        found_id = workflow_manager.get_workflow_id_by_name(sample_workflow_create.name)
        
        assert found_id == created.id

    def test_get_workflow_id_by_name_nonexistent(self, workflow_manager):
        """Test get_workflow_id_by_name returns None for non-existent name."""
        result = workflow_manager.get_workflow_id_by_name("non-existent-name")
        assert result is None

    def test_update_workflow(self, workflow_manager, sample_workflow_create):
        """Test update_workflow modifies existing workflow."""
        # Create workflow
        workflow = workflow_manager.create_workflow(sample_workflow_create)
        
        # Update workflow
        update_data = WorkflowUpdate(
            name="Updated Workflow",
            description="Updated description"
        )
        updated = workflow_manager.update_workflow(workflow.id, update_data)
        
        assert updated.id == workflow.id
        assert updated.name == "Updated Workflow"
        assert updated.description == "Updated description"

    def test_update_workflow_nonexistent(self, workflow_manager):
        """Test update_workflow raises error for non-existent workflow."""
        update_data = WorkflowUpdate(name="Updated")
        
        with pytest.raises(ValueError, match="Workflow .* not found"):
            workflow_manager.update_workflow("non-existent-id", update_data)

    def test_delete_workflow(self, workflow_manager, sample_workflow_create, temp_project_root):
        """Test delete_workflow removes workflow."""
        # Create workflow
        workflow = workflow_manager.create_workflow(sample_workflow_create)
        workflow_file = temp_project_root / "config" / "workflows" / f"{workflow.id}.json"
        assert workflow_file.exists()
        
        # Delete workflow
        result = workflow_manager.delete_workflow(workflow.id)
        
        assert result is True
        assert not workflow_file.exists()
        assert workflow_manager.get_workflow(workflow.id) is None

    def test_delete_workflow_nonexistent(self, workflow_manager):
        """Test delete_workflow returns False for non-existent workflow."""
        result = workflow_manager.delete_workflow("non-existent-id")
        assert result is False

    def test_set_active_workflow(self, workflow_manager, sample_workflow_create):
        """Test set_active_workflow sets active workflow."""
        workflow = workflow_manager.create_workflow(sample_workflow_create)
        
        workflow_manager.set_active_workflow(workflow.id)
        
        assert workflow_manager.active_workflow_id == workflow.id

    def test_set_active_workflow_nonexistent(self, workflow_manager):
        """Test set_active_workflow raises error for non-existent workflow."""
        with pytest.raises(ValueError, match="Workflow .* not found"):
            workflow_manager.set_active_workflow("non-existent-id")

    def test_clear_active_workflow(self, workflow_manager, sample_workflow_create):
        """Test clear_active_workflow clears active workflow."""
        workflow = workflow_manager.create_workflow(sample_workflow_create, make_active=True)
        assert workflow_manager.active_workflow_id == workflow.id
        
        workflow_manager.clear_active_workflow()
        assert workflow_manager.active_workflow_id is None

    def test_duplicate_workflow(self, workflow_manager, sample_workflow_create):
        """Test duplicate_workflow creates copy of existing workflow."""
        # Create original workflow
        original = workflow_manager.create_workflow(sample_workflow_create)
        
        # Duplicate workflow
        duplicated = workflow_manager.duplicate_workflow(original.id, "Duplicated Workflow")
        
        assert duplicated.id != original.id
        assert duplicated.name == "Duplicated Workflow"
        assert duplicated.description == original.description
        assert duplicated.nodes == original.nodes
        assert duplicated.edges == original.edges

    def test_duplicate_workflow_nonexistent(self, workflow_manager):
        """Test duplicate_workflow raises error for non-existent workflow."""
        with pytest.raises(ValueError, match="Workflow .* not found"):
            workflow_manager.duplicate_workflow("non-existent-id", "New Name")

    def test_workflow_with_nodes_and_edges(self, workflow_manager, sample_workflow_create):
        """Test workflow operations with nodes and edges."""
        # Create workflow
        workflow = workflow_manager.create_workflow(sample_workflow_create)
        
        # Add nodes
        node1_id = str(uuid.uuid4())
        node2_id = str(uuid.uuid4())
        
        node1 = WorkflowNode(
            id=node1_id,
            type="assistant",
            position={"x": 100, "y": 100},
            data=WorkflowNodeData(
                assistantId="assistant-1",
                assistantName="Assistant 1",
                isStart=True
            )
        )
        
        node2 = WorkflowNode(
            id=node2_id,
            type="assistant",
            position={"x": 300, "y": 100},
            data=WorkflowNodeData(
                assistantId="assistant-2",
                assistantName="Assistant 2",
                isStart=False
            )
        )
        
        edge = WorkflowEdge(
            id=str(uuid.uuid4()),
            source=node1_id,
            target=node2_id,
            data=WorkflowEdgeData(mode="single")
        )
        
        # Update workflow with nodes and edges
        workflow.nodes = [node1, node2]
        workflow.edges = [edge]
        workflow_manager.save_workflow(workflow)
        
        # Retrieve and verify
        retrieved = workflow_manager.get_workflow(workflow.id)
        assert len(retrieved.nodes) == 2
        assert len(retrieved.edges) == 1
        assert retrieved.nodes[0].id == node1_id
        assert retrieved.nodes[1].id == node2_id
        assert retrieved.edges[0].source == node1_id
        assert retrieved.edges[0].target == node2_id

    def test_cleanup_workflows_for_deleted_assistant(self, workflow_manager, sample_workflow_create):
        """Test cleanup_workflows_for_deleted_assistant removes assistant references."""
        # Create workflow with assistant nodes
        workflow = workflow_manager.create_workflow(sample_workflow_create)
        
        assistant_id_to_delete = "assistant-to-delete"
        assistant_id_to_keep = "assistant-to-keep"
        
        node1 = WorkflowNode(
            id=str(uuid.uuid4()),
            type="assistant",
            position={"x": 100, "y": 100},
            data=WorkflowNodeData(
                assistantId=assistant_id_to_delete,
                assistantName="Assistant to Delete",
                isStart=True
            )
        )
        
        node2 = WorkflowNode(
            id=str(uuid.uuid4()),
            type="assistant",
            position={"x": 300, "y": 100},
            data=WorkflowNodeData(
                assistantId=assistant_id_to_keep,
                assistantName="Assistant to Keep",
                isStart=False
            )
        )
        
        edge = WorkflowEdge(
            id=str(uuid.uuid4()),
            source=node1.id,
            target=node2.id,
            data=WorkflowEdgeData(mode="single")
        )
        
        workflow.nodes = [node1, node2]
        workflow.edges = [edge]
        workflow_manager.save_workflow(workflow)
        
        # Cleanup assistant
        modified_workflows = workflow_manager.cleanup_workflows_for_deleted_assistant(assistant_id_to_delete)
        
        # Verify cleanup
        assert workflow.id in modified_workflows
        
        updated_workflow = workflow_manager.get_workflow(workflow.id)
        assert len(updated_workflow.nodes) == 1
        assert len(updated_workflow.edges) == 0
        assert updated_workflow.nodes[0].data.assistantId == assistant_id_to_keep

    def test_register_rebuild_callback(self, workflow_manager):
        """Test register_rebuild_callback adds callback to list."""
        callback_called = False
        
        def test_callback(workflow_id: str):
            nonlocal callback_called
            callback_called = True
        
        workflow_manager.register_rebuild_callback(test_callback)
        
        # Trigger callback by creating workflow
        workflow = workflow_manager.create_workflow(WorkflowCreate(name="Test", description="Test"))
        
        # Manually trigger callback to test
        for callback in workflow_manager._callbacks:
            callback(workflow.id)
        
        assert callback_called

    def test_workflow_persistence_across_manager_instances(self, mock_config_manager, mock_log_manager, temp_project_root, sample_workflow_create):
        """Test that workflows persist across different manager instances."""
        # Create workflow with first manager
        manager1 = WorkflowManager(
            config_manager=mock_config_manager,
            log_manager=mock_log_manager,
            workflows_dir=temp_project_root / "config" / "workflows",
            auto_set_active_if_missing=False
        )
        workflow = manager1.create_workflow(sample_workflow_create)
        
        # Create second manager and verify workflow exists
        manager2 = WorkflowManager(
            config_manager=mock_config_manager,
            log_manager=mock_log_manager,
            workflows_dir=temp_project_root / "config" / "workflows",
            auto_set_active_if_missing=False
        )
        
        retrieved = manager2.get_workflow(workflow.id)
        assert retrieved is not None
        assert retrieved.id == workflow.id
        assert retrieved.name == workflow.name

    def test_auto_set_active_if_missing(self, mock_config_manager, mock_log_manager, temp_project_root, sample_workflow_create):
        """Test auto_set_active_if_missing functionality."""
        # Create manager with auto_set_active_if_missing=True
        manager = WorkflowManager(
            config_manager=mock_config_manager,
            log_manager=mock_log_manager,
            workflows_dir=temp_project_root / "config" / "workflows",
            auto_set_active_if_missing=True
        )
        
        # Initially no active workflow
        assert manager.active_workflow_id is None
        
        # Create workflow
        workflow = manager.create_workflow(sample_workflow_create)
        
        # Should be automatically set as active
        assert manager.active_workflow_id == workflow.id

    def test_workflow_name_uniqueness_not_enforced(self, workflow_manager):
        """Test that workflow names don't need to be unique."""
        # Create first workflow
        workflow1 = workflow_manager.create_workflow(WorkflowCreate(name="Same Name", description="First"))
        
        # Create second workflow with same name
        workflow2 = workflow_manager.create_workflow(WorkflowCreate(name="Same Name", description="Second"))
        
        assert workflow1.id != workflow2.id
        assert workflow1.name == workflow2.name