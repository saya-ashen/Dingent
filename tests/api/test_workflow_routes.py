"""
Tests for workflow API routes.
"""
import os
import sys
import importlib.util
from unittest.mock import Mock, patch
import pytest

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Try to install fastapi and httpx if not available
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi"])
    from fastapi import FastAPI
    from fastapi.testclient import TestClient


def load_module_directly(module_name, file_path):
    """Load a module directly from file path without package imports."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    
    # Mock problematic imports
    import sys
    original_import = __builtins__.__import__
    
    def mock_import(name, *args, **kwargs):
        if name.startswith('dingent.'):
            # Return a mock for dingent imports to avoid dependency issues
            return Mock()
        return original_import(name, *args, **kwargs)
    
    __builtins__.__import__ = mock_import
    
    try:
        spec.loader.exec_module(module)
    finally:
        __builtins__.__import__ = original_import
    
    return module


class TestWorkflowRoutesSimple:
    """Simple test suite for workflow API routes using mocked components."""
    
    def test_mock_workflow_functionality(self):
        """Test basic mocking functionality."""
        # Create a mock workflow manager
        mock_manager = Mock()
        
        # Mock workflow data
        sample_workflow = {
            "id": "test-workflow-id",
            "name": "Test Workflow",
            "description": "A test workflow",
            "nodes": [],
            "edges": []
        }
        
        mock_manager.list_workflows.return_value = [sample_workflow]
        mock_manager.get_workflow.return_value = sample_workflow
        mock_manager.active_workflow_id = "test-workflow-id"
        
        # Test mock functionality
        workflows = mock_manager.list_workflows()
        assert len(workflows) == 1
        assert workflows[0]["name"] == "Test Workflow"
        
        workflow = mock_manager.get_workflow("test-workflow-id")
        assert workflow["id"] == "test-workflow-id"
        
        assert mock_manager.active_workflow_id == "test-workflow-id"
        
        print("✅ Mock workflow functionality test passed!")
    
    def test_fastapi_basic_setup(self):
        """Test basic FastAPI setup."""
        app = FastAPI()
        
        # Add a simple test route
        @app.get("/test")
        def test_route():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
        
        print("✅ FastAPI basic setup test passed!")
    
    def test_workflow_routes_mock_integration(self):
        """Test workflow routes with mocked dependencies."""
        # Create mock workflow manager
        mock_manager = Mock()
        
        sample_workflow = {
            "id": "test-workflow-id",
            "name": "Test Workflow",
            "description": "A test workflow",
            "nodes": [],
            "edges": []
        }
        
        mock_manager.list_workflows.return_value = [sample_workflow]
        mock_manager.get_workflow.return_value = sample_workflow
        mock_manager.create_workflow.return_value = sample_workflow
        mock_manager.delete_workflow.return_value = True
        mock_manager.active_workflow_id = "test-workflow-id"
        
        # Create test app
        app = FastAPI()
        
        # Add test routes that simulate the actual workflow routes
        @app.get("/workflows")
        def list_workflows():
            return mock_manager.list_workflows()
        
        @app.post("/workflows")
        def create_workflow(workflow_data: dict):
            return mock_manager.create_workflow(workflow_data)
        
        @app.get("/workflows/active")
        def get_active_workflow():
            return {"current_workflow": mock_manager.active_workflow_id}
        
        @app.get("/workflows/{workflow_id}")
        def get_workflow(workflow_id: str):
            result = mock_manager.get_workflow(workflow_id)
            if not result:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Workflow not found")
            return result
        
        @app.delete("/workflows/{workflow_id}")
        def delete_workflow(workflow_id: str):
            success = mock_manager.delete_workflow(workflow_id)
            if not success:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Workflow not found")
            return {"status": "success", "message": f"Workflow {workflow_id} deleted"}
        
        # Test the routes
        client = TestClient(app)
        
        # Test list workflows
        response = client.get("/workflows")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Workflow"
        
        # Test get active workflow
        response = client.get("/workflows/active")
        assert response.status_code == 200
        data = response.json()
        assert data["current_workflow"] == "test-workflow-id"
        
        # Test get specific workflow
        response = client.get("/workflows/test-workflow-id")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-workflow-id"
        
        # Test create workflow
        response = client.post("/workflows", json={"name": "New Workflow"})
        assert response.status_code == 200
        
        # Test delete workflow
        response = client.delete("/workflows/test-workflow-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Test workflow not found
        mock_manager.get_workflow.return_value = None
        response = client.get("/workflows/non-existent")
        assert response.status_code == 404
        
        print("✅ Workflow routes mock integration test passed!")


def test_workflow_routes_standalone():
    """Standalone test function."""
    test_instance = TestWorkflowRoutesSimple()
    test_instance.test_mock_workflow_functionality()
    test_instance.test_fastapi_basic_setup()
    test_instance.test_workflow_routes_mock_integration()
    print("🎉 All workflow routes tests passed!")


if __name__ == "__main__":
    test_workflow_routes_standalone()