from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import toml

from dingent.core.plugin_manager import PluginManager, ResourceMiddleware
from dingent.core.resource_manager import ResourceManager
from dingent.core.types import PluginUserConfig


@pytest.fixture
def fake_plugin_dir(tmp_project_root: Path) -> Path:
    """Creates a fake plugin directory with a valid plugin."""
    plugin_dir = tmp_project_root / "plugins"
    my_plugin = plugin_dir / "my-plugin"
    my_plugin.mkdir()

    manifest_content = {
        "plugin": {
            "id": "my-plugin-id",
            "name": "My Test Plugin",
            "version": "1.0.0",
            "execution": {"mode": "local", "script_path": "main.py"},
            "config_schema": [{"name": "api_key", "type": "string", "secret": True, "required": True}],
        }
    }
    (my_plugin / "plugin.toml").write_text(toml.dumps(manifest_content))
    return plugin_dir


@pytest.mark.asyncio
async def test_plugin_manager_scan_and_create_instance(fake_plugin_dir, mock_log_manager):
    """Test scanning for plugins and creating a runnable instance."""
    rm = ResourceManager(mock_log_manager)
    pm = PluginManager(plugin_dir=fake_plugin_dir, resource_manager=rm, log_manager=mock_log_manager)

    # Test discovery
    assert "my-plugin-id" in pm.list_plugins()
    manifest = pm.get_plugin_manifest("my-plugin-id")
    assert manifest is not None
    assert manifest.name == "My Test Plugin"

    # Test instance creation
    user_config = PluginUserConfig(plugin_id="my-plugin-id", enabled=True, config={"api_key": "secret_value"})

    # We need to mock the transport and the proxy it creates
    with patch("dingent.core.plugin_manager.UvStdioTransport") as mock_transport, patch("dingent.core.plugin_manager.FastMCP.as_proxy") as mock_proxy:
        mock_proxy.return_value.get_tools = AsyncMock(return_value={})

        instance = await pm.create_instance(user_config)

        assert instance is not None
        assert instance.status == "active"
        assert instance.name == "My Test Plugin"

        # Check that the transport was initialized correctly
        mock_transport.assert_called_once()
        call_args = mock_transport.call_args[1]
        assert call_args["env_vars"]["api_key"] == "secret_value"


@pytest.mark.asyncio
async def test_resource_middleware(mock_log_manager):
    """Test that the middleware correctly wraps tool results."""
    rm = ResourceManager()
    middleware = ResourceMiddleware(rm, mock_log_manager.log_with_context)

    # Mock context and call_next
    mock_context = MagicMock()
    mock_context.fastmcp_context = {}

    # Mock the original tool result
    original_result = Mock()
    original_result.structured_content = {"data": "some_value"}
    original_result.content = [Mock(text='{"data": "some_value"}')]

    async def call_next(context):
        return original_result

    # Run the middleware
    final_result = await middleware.on_call_tool(mock_context, call_next)

    # Assertions
    assert "artifact_id" in final_result.structured_content
    assert final_result.structured_content["model_text"] == '{"data": "some_value"}'

    artifact_id = final_result.structured_content["artifact_id"]
    registered_resource = rm.get(artifact_id)
    assert registered_resource is not None
    assert registered_resource.content == {"data": "some_value"}
