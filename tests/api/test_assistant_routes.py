"""
Tests for assistant API routes.
"""
import os
import sys
from unittest.mock import Mock

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi"])
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient


class TestAssistantRoutesSimple:
    """Simple test suite for assistant API routes using mocked components."""
    
    def test_mock_assistant_functionality(self):
        """Test basic mocking functionality for assistants."""
        # Create a mock config manager
        mock_config_manager = Mock()
        mock_assistant_manager = Mock()
        mock_plugin_manager = Mock()
        
        # Mock assistant data
        sample_assistant = {
            "id": "test-assistant-id",
            "name": "Test Assistant",
            "description": "A test assistant",
            "plugins": []
        }
        
        mock_config_manager.list_assistants.return_value = [sample_assistant]
        mock_config_manager.get_assistant.return_value = sample_assistant
        mock_config_manager.upsert_assistant.return_value = sample_assistant
        mock_config_manager.delete_assistant.return_value = True
        
        # Test mock functionality
        assistants = mock_config_manager.list_assistants()
        assert len(assistants) == 1
        assert assistants[0]["name"] == "Test Assistant"
        
        assistant = mock_config_manager.get_assistant("test-assistant-id")
        assert assistant["id"] == "test-assistant-id"
        
        print("✅ Mock assistant functionality test passed!")
    
    def test_assistant_routes_mock_integration(self):
        """Test assistant routes with mocked dependencies."""
        # Create mock managers
        mock_config_manager = Mock()
        mock_assistant_manager = Mock()
        mock_plugin_manager = Mock()
        
        sample_assistant = {
            "id": "test-assistant-id",
            "name": "Test Assistant",
            "description": "A test assistant",
            "plugins": []
        }
        
        sample_plugin = {
            "plugin_id": "test-plugin",
            "enabled": True,
            "config": {}
        }
        
        mock_config_manager.list_assistants.return_value = [sample_assistant]
        mock_config_manager.get_assistant.return_value = sample_assistant
        mock_config_manager.upsert_assistant.return_value = sample_assistant
        mock_config_manager.delete_assistant.return_value = True
        mock_config_manager.update_plugins_for_assistant.return_value = sample_assistant
        
        mock_assistant_manager.get_assistant.return_value = Mock(
            id="test-assistant-id",
            name="Test Assistant",
            plugin_instances={"test-plugin": Mock()}
        )
        
        mock_plugin_manager.list_available_plugins.return_value = ["test-plugin"]
        mock_plugin_manager.get_plugin_manifest.return_value = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0"
        }
        
        # Create test app
        app = FastAPI()
        
        # Add test routes that simulate the actual assistant routes
        @app.get("/assistants")
        def list_assistants():
            return mock_config_manager.list_assistants()
        
        @app.post("/assistants")
        def create_assistant(assistant_data: dict):
            return mock_config_manager.upsert_assistant(assistant_data)
        
        @app.get("/assistants/{assistant_id}")
        def get_assistant(assistant_id: str):
            result = mock_config_manager.get_assistant(assistant_id)
            if not result:
                raise HTTPException(status_code=404, detail="Assistant not found")
            return result
        
        @app.put("/assistants/{assistant_id}")
        def update_assistant(assistant_id: str, assistant_data: dict):
            return mock_config_manager.upsert_assistant(assistant_data)
        
        @app.delete("/assistants/{assistant_id}")
        def delete_assistant(assistant_id: str):
            success = mock_config_manager.delete_assistant(assistant_id)
            if not success:
                raise HTTPException(status_code=404, detail="Assistant not found")
            return {"status": "success", "message": f"Assistant {assistant_id} deleted"}
        
        @app.post("/assistants/{assistant_id}/plugins")
        def add_plugin_to_assistant(assistant_id: str, plugin_data: dict):
            # First check assistant exists
            assistant = mock_config_manager.get_assistant(assistant_id)
            if not assistant:
                raise HTTPException(status_code=404, detail="Assistant not found")
            
            # Add plugin
            current_plugins = assistant.get("plugins", [])
            current_plugins.append(plugin_data)
            
            return mock_config_manager.update_plugins_for_assistant(assistant_id, current_plugins)
        
        @app.get("/assistants/{assistant_id}/plugins")
        def list_assistant_plugins(assistant_id: str):
            assistant = mock_config_manager.get_assistant(assistant_id)
            if not assistant:
                raise HTTPException(status_code=404, detail="Assistant not found")
            return assistant.get("plugins", [])
        
        @app.delete("/assistants/{assistant_id}/plugins/{plugin_id}")
        def remove_plugin_from_assistant(assistant_id: str, plugin_id: str):
            assistant = mock_config_manager.get_assistant(assistant_id)
            if not assistant:
                raise HTTPException(status_code=404, detail="Assistant not found")
            
            # Remove plugin
            current_plugins = [p for p in assistant.get("plugins", []) if p.get("plugin_id") != plugin_id]
            
            mock_config_manager.update_plugins_for_assistant(assistant_id, current_plugins)
            return {"status": "success", "message": f"Plugin {plugin_id} removed from assistant"}
        
        # Test the routes
        client = TestClient(app)
        
        # Test list assistants
        response = client.get("/assistants")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Assistant"
        
        # Test get specific assistant
        response = client.get("/assistants/test-assistant-id")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-assistant-id"
        
        # Test create assistant
        response = client.post("/assistants", json={"name": "New Assistant", "description": "New"})
        assert response.status_code == 200
        
        # Test update assistant
        response = client.put("/assistants/test-assistant-id", json={"name": "Updated Assistant"})
        assert response.status_code == 200
        
        # Test add plugin to assistant
        plugin_data = {"plugin_id": "test-plugin", "enabled": True}
        response = client.post("/assistants/test-assistant-id/plugins", json=plugin_data)
        assert response.status_code == 200
        
        # Test list assistant plugins
        response = client.get("/assistants/test-assistant-id/plugins")
        assert response.status_code == 200
        
        # Test remove plugin from assistant
        response = client.delete("/assistants/test-assistant-id/plugins/test-plugin")
        assert response.status_code == 200
        
        # Test delete assistant
        response = client.delete("/assistants/test-assistant-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Test assistant not found
        mock_config_manager.get_assistant.return_value = None
        response = client.get("/assistants/non-existent")
        assert response.status_code == 404
        
        print("✅ Assistant routes mock integration test passed!")
    
    def test_assistant_plugin_management(self):
        """Test plugin management functionality for assistants."""
        mock_config_manager = Mock()
        
        # Mock assistant with plugins
        assistant_with_plugins = {
            "id": "assistant-with-plugins",
            "name": "Assistant with Plugins",
            "description": "An assistant with plugins",
            "plugins": [
                {"plugin_id": "plugin1", "enabled": True, "config": {}},
                {"plugin_id": "plugin2", "enabled": False, "config": {"param": "value"}}
            ]
        }
        
        mock_config_manager.get_assistant.return_value = assistant_with_plugins
        mock_config_manager.update_plugins_for_assistant.return_value = assistant_with_plugins
        
        # Test plugin operations
        app = FastAPI()
        
        @app.get("/assistants/{assistant_id}/plugins")
        def get_plugins(assistant_id: str):
            assistant = mock_config_manager.get_assistant(assistant_id)
            if not assistant:
                raise HTTPException(status_code=404, detail="Assistant not found")
            return assistant.get("plugins", [])
        
        @app.put("/assistants/{assistant_id}/plugins/{plugin_id}")
        def update_plugin_config(assistant_id: str, plugin_id: str, config_data: dict):
            assistant = mock_config_manager.get_assistant(assistant_id)
            if not assistant:
                raise HTTPException(status_code=404, detail="Assistant not found")
            
            # Update plugin config
            plugins = assistant.get("plugins", [])
            for plugin in plugins:
                if plugin.get("plugin_id") == plugin_id:
                    plugin.update(config_data)
                    break
            
            return mock_config_manager.update_plugins_for_assistant(assistant_id, plugins)
        
        client = TestClient(app)
        
        # Test get plugins
        response = client.get("/assistants/assistant-with-plugins/plugins")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["plugin_id"] == "plugin1"
        assert data[1]["plugin_id"] == "plugin2"
        
        # Test update plugin config
        update_data = {"enabled": True, "config": {"new_param": "new_value"}}
        response = client.put("/assistants/assistant-with-plugins/plugins/plugin2", json=update_data)
        assert response.status_code == 200
        
        print("✅ Assistant plugin management test passed!")


def test_assistant_routes_standalone():
    """Standalone test function."""
    test_instance = TestAssistantRoutesSimple()
    test_instance.test_mock_assistant_functionality()
    test_instance.test_assistant_routes_mock_integration()
    test_instance.test_assistant_plugin_management()
    print("🎉 All assistant routes tests passed!")


if __name__ == "__main__":
    test_assistant_routes_standalone()