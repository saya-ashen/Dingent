"""
Tests for ConfigManager - configuration loading, saving, validation, and assistants CRUD.
"""
import json
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import tomlkit
from pydantic import ValidationError

from dingent.core.config_manager import ConfigManager
from dingent.core.settings import AssistantSettings, LLMSettings
from dingent.core.types import AssistantCreate, AssistantUpdate, PluginUserConfig


class TestConfigManager:
    """Test suite for ConfigManager."""

    def test_config_manager_initialization(self, temp_project_root, mock_log_manager):
        """Test ConfigManager initializes correctly."""
        config_manager = ConfigManager(temp_project_root, mock_log_manager)
        
        assert config_manager.project_root == temp_project_root
        assert config_manager.log_manager == mock_log_manager
        assert config_manager._dir == temp_project_root / "config"
        assert config_manager._assistants_dir == temp_project_root / "config" / "assistants"
        assert config_manager._plugins_dir == temp_project_root / "config" / "plugins"

    def test_get_settings_loads_from_disk(self, isolated_config_manager):
        """Test get_settings loads configuration from disk."""
        settings = isolated_config_manager.get_settings()
        
        assert settings is not None
        assert hasattr(settings, 'llm')
        assert hasattr(settings, 'assistants')
        assert hasattr(settings, 'workflows')

    def test_list_assistants_empty_initially(self, isolated_config_manager):
        """Test list_assistants returns empty list initially."""
        assistants = isolated_config_manager.list_assistants()
        assert assistants == []

    def test_upsert_assistant_create_new(self, isolated_config_manager, sample_assistant_create):
        """Test upsert_assistant creates new assistant."""
        result = isolated_config_manager.upsert_assistant(sample_assistant_create)
        
        assert isinstance(result, AssistantSettings)
        assert result.name == sample_assistant_create.name
        assert result.description == sample_assistant_create.description
        assert result.id is not None
        assert len(result.id) > 0

    def test_upsert_assistant_creates_file(self, isolated_config_manager, sample_assistant_create, temp_project_root):
        """Test upsert_assistant creates assistant file on disk."""
        result = isolated_config_manager.upsert_assistant(sample_assistant_create)
        
        # Check that file was created
        assistant_file = temp_project_root / "config" / "assistants" / f"{result.id}.yaml"
        assert assistant_file.exists()

    def test_get_assistant_existing(self, isolated_config_manager, sample_assistant_create):
        """Test get_assistant retrieves existing assistant."""
        created = isolated_config_manager.upsert_assistant(sample_assistant_create)
        retrieved = isolated_config_manager.get_assistant(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.description == created.description

    def test_get_assistant_nonexistent(self, isolated_config_manager):
        """Test get_assistant returns None for non-existent assistant."""
        result = isolated_config_manager.get_assistant("non-existent-id")
        assert result is None

    def test_upsert_assistant_update_existing(self, isolated_config_manager, sample_assistant_create):
        """Test upsert_assistant updates existing assistant."""
        # Create assistant
        created = isolated_config_manager.upsert_assistant(sample_assistant_create)
        
        # Update with new data
        update_data = AssistantUpdate(
            id=created.id,
            name="Updated Name",
            description="Updated description"
        )
        updated = isolated_config_manager.upsert_assistant(update_data)
        
        assert updated.id == created.id
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"

    def test_delete_assistant_existing(self, isolated_config_manager, sample_assistant_create, temp_project_root):
        """Test delete_assistant removes existing assistant."""
        # Create assistant
        created = isolated_config_manager.upsert_assistant(sample_assistant_create)
        assistant_file = temp_project_root / "config" / "assistants" / f"{created.id}.yaml"
        assert assistant_file.exists()
        
        # Delete assistant
        result = isolated_config_manager.delete_assistant(created.id)
        
        assert result is True
        assert not assistant_file.exists()

    def test_delete_assistant_nonexistent(self, isolated_config_manager):
        """Test delete_assistant returns False for non-existent assistant."""
        result = isolated_config_manager.delete_assistant("non-existent-id")
        assert result is False

    def test_list_assistants_after_operations(self, isolated_config_manager, sample_assistant_create):
        """Test list_assistants reflects CRUD operations."""
        # Initially empty
        assert len(isolated_config_manager.list_assistants()) == 0
        
        # Create first assistant
        assistant1 = isolated_config_manager.upsert_assistant(sample_assistant_create)
        assistants = isolated_config_manager.list_assistants()
        assert len(assistants) == 1
        assert assistants[0].id == assistant1.id
        
        # Create second assistant
        assistant2_data = AssistantCreate(name="Assistant 2", description="Second assistant")
        assistant2 = isolated_config_manager.upsert_assistant(assistant2_data)
        assistants = isolated_config_manager.list_assistants()
        assert len(assistants) == 2
        
        # Delete first assistant
        isolated_config_manager.delete_assistant(assistant1.id)
        assistants = isolated_config_manager.list_assistants()
        assert len(assistants) == 1
        assert assistants[0].id == assistant2.id

    def test_update_plugins_for_assistant(self, isolated_config_manager, sample_assistant_create, plugin_user_config):
        """Test update_plugins_for_assistant updates plugin configurations."""
        # Create assistant
        assistant = isolated_config_manager.upsert_assistant(sample_assistant_create)
        
        # Update plugins
        plugin_configs = [plugin_user_config]
        updated = isolated_config_manager.update_plugins_for_assistant(assistant.id, plugin_configs)
        
        assert len(updated.plugins) == 1
        assert updated.plugins[0].plugin_id == plugin_user_config.plugin_id
        assert updated.plugins[0].enabled == plugin_user_config.enabled

    def test_update_global_settings(self, isolated_config_manager):
        """Test update_global updates global settings."""
        new_settings = {
            "current_workflow": "new-workflow-id"
        }
        
        result = isolated_config_manager.update_global(new_settings)
        
        assert result.current_workflow == "new-workflow-id"

    def test_on_change_callback_registration(self, isolated_config_manager):
        """Test on_change callback registration and triggering."""
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        isolated_config_manager.register_on_change(test_callback)
        
        # Trigger a change by creating an assistant
        isolated_config_manager.upsert_assistant(AssistantCreate(name="Test", description="Test"))
        
        assert callback_called

    def test_config_validation_error_handling(self, temp_project_root, mock_log_manager):
        """Test handling of configuration validation errors."""
        # Create invalid TOML file
        invalid_toml = """[llm]
model = 123  # Invalid: should be string
"""
        (temp_project_root / "dingent.toml").write_text(invalid_toml)
        
        with pytest.raises(ValidationError):
            ConfigManager(temp_project_root, mock_log_manager)

    def test_assistant_id_generation(self, isolated_config_manager):
        """Test that assistant IDs are properly generated."""
        assistant_data = AssistantCreate(name="Test Assistant", description="Test")
        result = isolated_config_manager.upsert_assistant(assistant_data)
        
        # Should be a valid UUID
        try:
            uuid.UUID(result.id)
        except ValueError:
            pytest.fail("Assistant ID should be a valid UUID")

    def test_concurrent_modifications_thread_safety(self, isolated_config_manager, sample_assistant_create):
        """Test thread safety during concurrent modifications."""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_assistant(name_suffix):
            try:
                assistant_data = AssistantCreate(
                    name=f"Assistant {name_suffix}", 
                    description=f"Test assistant {name_suffix}"
                )
                result = isolated_config_manager.upsert_assistant(assistant_data)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_assistant, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        assert len(set(r.id for r in results)) == 5  # All unique IDs

    def test_plugin_config_persistence(self, isolated_config_manager, sample_assistant_create, temp_project_root):
        """Test that plugin configurations are persisted to disk."""
        # Create assistant
        assistant = isolated_config_manager.upsert_assistant(sample_assistant_create)
        
        # Add plugin config
        plugin_config = PluginUserConfig(
            plugin_id="test-plugin",
            enabled=True,
            config={"key": "value"}
        )
        
        isolated_config_manager.update_plugins_for_assistant(assistant.id, [plugin_config])
        
        # Check that plugin config file was created
        plugin_file = temp_project_root / "config" / "plugins" / "test-plugin" / f"{assistant.id}.yaml"
        assert plugin_file.exists()
        
        # Check content
        import yaml
        with open(plugin_file) as f:
            content = yaml.safe_load(f)
        
        assert content["enabled"] is True
        assert content["config"]["key"] == "value"

    def test_reload_after_external_changes(self, isolated_config_manager, temp_project_root):
        """Test that manager can reload after external file changes."""
        # Create assistant file externally
        assistant_id = str(uuid.uuid4())
        assistant_file = temp_project_root / "config" / "assistants" / f"{assistant_id}.yaml"
        
        assistant_data = {
            "id": assistant_id,
            "name": "External Assistant",
            "description": "Created externally",
            "plugins": []
        }
        
        import yaml
        with open(assistant_file, 'w') as f:
            yaml.dump(assistant_data, f)
        
        # Reload and verify
        assistants = isolated_config_manager.list_assistants()
        external_assistant = next((a for a in assistants if a.id == assistant_id), None)
        
        assert external_assistant is not None
        assert external_assistant.name == "External Assistant"