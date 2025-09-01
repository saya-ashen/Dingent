"""
Pytest fixtures for testing core managers and components.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from pydantic import SecretStr

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dingent.core.log_manager import LogManager
from dingent.core.settings import AppSettings, AssistantSettings, LLMSettings
from dingent.core.types import AssistantCreate, PluginUserConfig, Workflow, WorkflowCreate


@pytest.fixture
def temp_project_root():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create basic directory structure
        (temp_path / "config" / "assistants").mkdir(parents=True)
        (temp_path / "config" / "plugins").mkdir(parents=True)
        (temp_path / "config" / "workflows").mkdir(parents=True)
        (temp_path / ".dingent" / "data").mkdir(parents=True)
        
        # Create basic dingent.toml
        toml_content = """[llm]
model = "test-model"

current_workflow = ""
"""
        (temp_path / "dingent.toml").write_text(toml_content)
        
        yield temp_path


@pytest.fixture
def mock_log_manager():
    """Create a mock log manager."""
    log_manager = Mock(spec=LogManager)
    log_manager.log_with_context = Mock()
    return log_manager


@pytest.fixture
def basic_app_settings():
    """Create basic app settings for testing."""
    return AppSettings(
        llm=LLMSettings(
            model="test-model",
            provider="test-provider",
            base_url="http://test.com",
            api_key=SecretStr("test-key")
        ),
        assistants=[],
        workflows=[],
        current_workflow=""
    )


@pytest.fixture
def sample_assistant_settings():
    """Create sample assistant settings for testing."""
    return AssistantSettings(
        id="test-assistant-id",
        name="Test Assistant",
        description="A test assistant",
        plugins=[]
    )


@pytest.fixture
def sample_assistant_create():
    """Create sample assistant create data."""
    return AssistantCreate(
        name="New Assistant",
        description="A new test assistant"
    )


@pytest.fixture
def sample_workflow_create():
    """Create sample workflow create data."""
    return WorkflowCreate(
        name="Test Workflow",
        description="A test workflow"
    )


@pytest.fixture
def sample_workflow():
    """Create a sample workflow."""
    return Workflow(
        id="test-workflow-id",
        name="Test Workflow",
        description="A test workflow",
        nodes=[],
        edges=[]
    )


# Mock external dependencies that might not be available in test environment
@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch):
    """Mock external dependencies that might not be available."""
    # Mock langchain components
    mock_chat_model = Mock()
    mock_chat_model.invoke = Mock(return_value="mocked response")
    
    # Mock any other external dependencies as needed
    try:
        from unittest.mock import patch
        with patch('langchain_litellm.ChatLiteLLM', return_value=mock_chat_model):
            yield
    except ImportError:
        # If langchain_litellm is not available, just yield
        yield


@pytest.fixture
def plugin_user_config():
    """Create a sample plugin user config."""
    return PluginUserConfig(
        plugin_id="test-plugin",
        enabled=True,
        config={"param1": "value1"}
    )


class MockPluginInstance:
    """Mock plugin instance for testing."""
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self.status = "active"
        self.tools = []
    
    async def aclose(self):
        pass


@pytest.fixture
def mock_plugin_instance():
    """Create a mock plugin instance."""
    return MockPluginInstance("test-plugin")


class MockAssistant:
    """Mock assistant for testing."""
    def __init__(self, assistant_id: str, name: str, description: str = "", plugin_instances=None):
        self.id = assistant_id
        self.name = name
        self.description = description
        self.plugin_instances = plugin_instances or {}
    
    async def aclose(self):
        pass


@pytest.fixture
def mock_assistant():
    """Create a mock assistant."""
    return MockAssistant("test-assistant", "Test Assistant")