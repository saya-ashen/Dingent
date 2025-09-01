"""
Simple test script for LLMManager to validate our testing approach.
"""
import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from unittest.mock import Mock, patch

# Import modules directly without package to avoid __init__.py
import importlib.util

# Load log_manager module directly
log_manager_spec = importlib.util.spec_from_file_location(
    "log_manager", 
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "dingent", "core", "log_manager.py")
)
log_manager_module = importlib.util.module_from_spec(log_manager_spec)
log_manager_spec.loader.exec_module(log_manager_module)
LogManager = log_manager_module.LogManager

# Load llm_manager module directly
llm_manager_spec = importlib.util.spec_from_file_location(
    "llm_manager", 
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "dingent", "core", "llm_manager.py")
)
llm_manager_module = importlib.util.module_from_spec(llm_manager_spec)

# Mock the log_manager dependency in llm_manager_module
import sys
sys.modules['dingent.core.log_manager'] = log_manager_module

llm_manager_spec.loader.exec_module(llm_manager_module)
LLMManager = llm_manager_module.LLMManager


def test_llm_manager_basic():
    """Test basic LLMManager functionality."""
    # Create mock log manager
    mock_log_manager = Mock()
    mock_log_manager.log_with_context = Mock()
    
    # Create LLMManager
    llm_manager = LLMManager(mock_log_manager)
    
    # Test initialization
    assert llm_manager._llms == {}
    assert llm_manager._log_manager == mock_log_manager
    
    # Test list_available_llms when empty
    assert llm_manager.list_available_llms() == []
    
    print("✅ Basic LLMManager test passed!")


def test_llm_manager_with_mocked_llm():
    """Test LLMManager with mocked LLM creation."""
    # Create mock log manager
    mock_log_manager = Mock()
    mock_log_manager.log_with_context = Mock()
    
    # Create LLMManager
    llm_manager = LLMManager(mock_log_manager)
    
    # Mock ChatLiteLLM directly on the module
    with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
        mock_llm_instance = Mock()
        mock_chat_litellm.return_value = mock_llm_instance
        
        # Test get_llm
        result = llm_manager.get_llm(model="test-model", api_key="test-key")
        
        # Verify result
        assert result == mock_llm_instance
        mock_chat_litellm.assert_called_once_with(
            model="test-model", 
            api_key="test-key", 
            api_base=None
        )
        
        # Verify logging
        mock_log_manager.log_with_context.assert_called_with(
            "info", 
            "LLM instance created and cached.", 
            context={"params": {"model": "test-model", "api_key": "***"}}
        )
        
        # Test caching - second call should not create new instance
        mock_chat_litellm.reset_mock()
        result2 = llm_manager.get_llm(model="test-model", api_key="test-key")
        assert result2 == mock_llm_instance
        mock_chat_litellm.assert_not_called()
        
        # Test list_available_llms
        available = llm_manager.list_available_llms()
        assert len(available) == 1
    
    print("✅ LLMManager with mocked LLM test passed!")


if __name__ == "__main__":
    test_llm_manager_basic()
    test_llm_manager_with_mocked_llm()
    print("🎉 All LLMManager tests passed!")