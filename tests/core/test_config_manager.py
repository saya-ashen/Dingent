from unittest.mock import Mock, patch

import pytest
import tomlkit
from pydantic import SecretStr

from dingent.core.config_manager import ConfigManager
from dingent.core.settings import AppSettings
from dingent.core.types import AssistantCreate, PluginUserConfig


# Mock the SecretManager to avoid dealing with the actual keyring
@pytest.fixture
def mock_secret_manager():
    with patch("dingent.core.config_manager.SecretManager") as mock:
        instance = mock.return_value
        instance.get_secret.side_effect = lambda key: f"decrypted_{key}"
        instance.set_secret = Mock()
        yield instance


def test_config_manager_initialization_empty(tmp_project_root, mock_log_manager, mock_secret_manager):
    """Test initialization with an empty directory."""
    cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)
    settings = cm.get_settings()
    assert settings.assistants == []
    assert settings.llm is not None


def test_upsert_and_get_assistant(tmp_project_root, mock_log_manager, mock_secret_manager):
    """Test creating, updating, and retrieving an assistant."""
    cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)

    # Create
    created_assistant = cm.upsert_assistant({"name": "Test Assistant", "description": "A test assistant.", "model": "gpt-4"})
    assert created_assistant.name == "Test Assistant"
    assert len(cm.list_assistants()) == 1

    # Verify file creation
    assistant_file = tmp_project_root / "config" / "assistants" / f"{created_assistant.id}.yaml"
    assert assistant_file.is_file()

    # Get
    retrieved = cm.get_assistant(created_assistant.id)
    assert retrieved is not None
    assert retrieved.id == created_assistant.id

    # Update
    updated_assistant = cm.upsert_assistant({"id": created_assistant.id, "description": "An updated description."})
    assert updated_assistant.description == "An updated description."

    reloaded_cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)
    reloaded_assistant = reloaded_cm.get_assistant(created_assistant.id)
    assert reloaded_assistant is not None
    assert reloaded_assistant.description == "An updated description."


def test_delete_assistant(tmp_project_root, mock_log_manager, mock_secret_manager):
    """Test deleting an assistant and its associated files."""
    cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)
    mock_assistant = AssistantCreate(id="to-delete", name="ToDelete", description="To be deleted", version="1.0", spec_version="1.0", enabled=True)
    assistant = cm.upsert_assistant(mock_assistant)
    mock_plugin = PluginUserConfig(plugin_id="test-plugin", enabled=True, config={})
    cm.update_plugins_for_assistant(assistant.id, [mock_plugin])

    assistant_file = tmp_project_root / "config" / "assistants" / f"{assistant.id}.yaml"
    plugin_file = tmp_project_root / "config" / "plugins" / "test-plugin" / f"{assistant.id}.yaml"

    assert assistant_file.exists()
    assert plugin_file.exists()

    result = cm.delete_assistant(assistant.id)
    assert result is True
    assert cm.get_assistant(assistant.id) is None
    assert not assistant_file.exists()
    assert not plugin_file.exists()


def test_update_global_settings(tmp_project_root, mock_log_manager, mock_secret_manager):
    """Test updating the global dingent.toml file."""
    cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)

    # Create an API key which is a secret
    api_key_update = {"llm": {"api_key": SecretStr("my_secret_key")}}
    cm.update_global(api_key_update)

    # Assert that the secret manager was called
    mock_secret_manager.set_secret.assert_called_with("llm.api_key", "my_secret_key")

    # Check that the file contains the placeholder
    global_config_path = tmp_project_root / "dingent.toml"
    content = tomlkit.parse(global_config_path.read_text())
    assert content["llm"]["api_key"] == "keyring:llm.api_key"

    # Reload and check if the secret is decrypted
    reloaded_cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)
    settings = reloaded_cm.get_settings()
    assert settings.llm.api_key.get_secret_value() == "decrypted_llm.api_key"


def test_transaction_context(tmp_project_root, mock_log_manager, mock_secret_manager):
    """Test that transactions commit on success and roll back on failure."""
    cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)

    # Successful transaction
    with cm.transaction():
        cm.upsert_assistant({"name": "txn_assistant"})

    assert len(cm.list_assistants()) == 1

    # Failed transaction
    try:
        with cm.transaction():
            cm.upsert_assistant({"name": "fail_assistant"})
            raise ValueError("Something went wrong")
    except ValueError:
        pass

    # The second assistant should not have been persisted
    assert len(cm.list_assistants()) == 1
    assert cm.get_assistant("fail_assistant") is None


def test_on_change_callback(tmp_project_root, mock_log_manager, mock_secret_manager):
    """Test that registered callbacks are fired upon configuration changes."""
    cm = ConfigManager(project_root=tmp_project_root, log_manager=mock_log_manager)
    callback = Mock()

    cm.register_on_change(callback)

    cm.update_global({"current_workflow": "new_workflow"})

    callback.assert_called_once()
    old_settings, new_settings = callback.call_args[0]
    assert isinstance(old_settings, AppSettings)
    assert isinstance(new_settings, AppSettings)
    assert new_settings.current_workflow == "new_workflow"

    cm.unregister_on_change(callback)
    cm.update_global({"current_workflow": "another_workflow"})
    callback.assert_called_once()  # Should not be called again
