from unittest.mock import AsyncMock, Mock

import pytest

from dingent.core.assistant_manager import Assistant, AssistantManager
from dingent.core.plugin_manager import PluginInstance
from dingent.core.settings import AppSettings, AssistantSettings


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager that returns predefined assistant settings."""
    cm = Mock()
    assistant1 = AssistantSettings(id="asst_1", name="Assistant One", enabled=True, plugins=[], description="First assistant", version="1.0", spec_version="1.0")
    assistant2 = AssistantSettings(id="asst_2", name="Assistant Two", enabled=False, plugins=[], description="Second assistant", version="1.0", spec_version="1.0")
    cm.list_assistants.return_value = [assistant1, assistant2]
    cm.get_assistant.side_effect = lambda aid: {"asst_1": assistant1, "asst_2": assistant2}.get(aid)
    cm.register_on_change = Mock()
    return cm


@pytest.fixture
def mock_plugin_manager():
    """Mock PluginManager that can create mock plugin instances."""
    pm = Mock()

    async def create_instance(pconf):
        inst = AsyncMock(spec=PluginInstance)
        inst.aclose = AsyncMock()
        return inst

    pm.create_instance = AsyncMock(side_effect=create_instance)
    return pm


@pytest.mark.asyncio
async def test_assistant_manager_lazy_load(mock_config_manager, mock_plugin_manager, mock_log_manager):
    """Test that assistants are created only when requested."""
    am = AssistantManager(mock_config_manager, mock_plugin_manager, mock_log_manager)

    # Initially, no instances should exist
    assert not am._assistants

    # Request an enabled assistant
    assistant_one = await am.get_assistant("asst_1")
    assert isinstance(assistant_one, Assistant)
    assert "asst_1" in am._assistants

    # Requesting a disabled assistant should fail
    with pytest.raises(ValueError):
        await am.get_assistant("asst_2")

    # Requesting a non-existent assistant should fail
    with pytest.raises(ValueError):
        await am.get_assistant("asst_nonexistent")

    await am.aclose()


@pytest.mark.asyncio
async def test_on_config_change_handling(mock_config_manager, mock_plugin_manager, mock_log_manager):
    """Test how the manager reacts to add, remove, and update events."""
    am = AssistantManager(mock_config_manager, mock_plugin_manager, mock_log_manager)

    # Preload an assistant to have an active instance
    await am.get_assistant("asst_1")
    initial_instance = am._assistants["asst_1"]
    initial_instance.aclose = AsyncMock()  # Add mock for assertion

    # 1. Simulate a config change: asst_1 is updated, asst_2 is removed, asst_3 is added
    asst1_updated = AssistantSettings(id="asst_1", name="Assistant One Updated", enabled=True, plugins=[], description="First assistant updated", version="1.1", spec_version="1.0")
    asst3_new = AssistantSettings(id="asst_3", name="Assistant Three", enabled=True, plugins=[], description="Third assistant", version="1.0", spec_version="1.0")

    old_app_settings = AppSettings(assistants=mock_config_manager.list_assistants(), current_workflow="")
    new_app_settings = AppSettings(assistants=[asst1_updated, asst3_new], current_workflow="")

    # Manually trigger the async handler
    await am._handle_config_change_async(old_app_settings, new_app_settings)

    # Assertions
    # Old instance of asst_1 should be closed and removed (because its hash changed)
    initial_instance.aclose.assert_called_once()
    assert "asst_1" not in am._assistants  # It's lazy, so it won't be recreated yet

    # asst_2 should be gone from the maps
    assert "asst_2" not in am._settings_map

    # asst_3 should be added to the maps but not instantiated
    assert "asst_3" in am._settings_map
    assert "asst_3" not in am._assistants

    # Now get the updated assistant, it should be a new instance
    reloaded_instance = await am.get_assistant("asst_1")
    assert reloaded_instance is not initial_instance
    assert reloaded_instance.name == "Assistant One Updated"

    await am.aclose()


@pytest.mark.asyncio
async def test_rebuild_and_aclose(mock_config_manager, mock_plugin_manager, mock_log_manager):
    """Test full rebuild and cleanup."""
    am = AssistantManager(mock_config_manager, mock_plugin_manager, mock_log_manager)

    # Load one assistant
    inst = await am.get_assistant("asst_1")
    inst.aclose = AsyncMock()

    assert "asst_1" in am._assistants

    # Rebuild
    await am.rebuild()

    # The instance should have been closed and cleared
    inst.aclose.assert_called_once()
    assert not am._assistants

    # The settings maps should be re-populated
    assert "asst_1" in am._settings_map
    assert "asst_2" in am._settings_map
