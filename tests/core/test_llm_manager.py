"""
Tests for LLMManager - core LLM instance management and caching.
"""
import os
import sys
import importlib.util
from unittest.mock import Mock, patch

import pytest

# Add src to Python path and import modules directly to avoid __init__.py issues
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

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
sys.modules['dingent.core.log_manager'] = log_manager_module

llm_manager_spec.loader.exec_module(llm_manager_module)
LLMManager = llm_manager_module.LLMManager

from pydantic import SecretStr


class TestLLMManager:
    """Test suite for LLMManager."""

    @pytest.fixture
    def mock_log_manager(self):
        """Create a mock log manager."""
        log_manager = Mock(spec=LogManager)
        log_manager.log_with_context = Mock()
        return log_manager

    @pytest.fixture
    def llm_manager(self, mock_log_manager):
        """Create an LLMManager instance for testing."""
        return LLMManager(mock_log_manager)

    def test_llm_manager_initialization(self, mock_log_manager):
        """Test LLMManager initializes correctly."""
        llm_manager = LLMManager(mock_log_manager)
        
        assert llm_manager._llms == {}
        assert llm_manager._log_manager == mock_log_manager

    def test_get_llm_creates_and_caches_instance(self, llm_manager):
        """Test that get_llm creates and caches LLM instances."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance = Mock()
            mock_chat_litellm.return_value = mock_llm_instance
            
            # First call should create instance
            result = llm_manager.get_llm(model="test-model", api_key="test-key")
            
            assert result == mock_llm_instance
            mock_chat_litellm.assert_called_once_with(
                model="test-model", 
                api_key="test-key", 
                api_base=None
            )
            
            # Second call with same params should return cached instance
            mock_chat_litellm.reset_mock()
            result2 = llm_manager.get_llm(model="test-model", api_key="test-key")
            
            assert result2 == mock_llm_instance
            mock_chat_litellm.assert_not_called()  # Should not create new instance

    def test_get_llm_with_secret_str_api_key(self, llm_manager):
        """Test get_llm handles SecretStr API keys correctly."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance = Mock()
            mock_chat_litellm.return_value = mock_llm_instance
            
            secret_key = SecretStr("secret-api-key")
            result = llm_manager.get_llm(model="test-model", api_key=secret_key)
            
            assert result == mock_llm_instance
            mock_chat_litellm.assert_called_once_with(
                model="test-model", 
                api_key="secret-api-key",  # Should extract secret value
                api_base=None
            )

    def test_get_llm_with_api_base(self, llm_manager):
        """Test get_llm handles api_base parameter."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance = Mock()
            mock_chat_litellm.return_value = mock_llm_instance
            
            result = llm_manager.get_llm(
                model="test-model", 
                api_key="test-key",
                api_base="https://api.example.com"
            )
            
            assert result == mock_llm_instance
            mock_chat_litellm.assert_called_once_with(
                model="test-model", 
                api_key="test-key", 
                api_base="https://api.example.com"
            )

    def test_get_llm_with_base_url_fallback(self, llm_manager):
        """Test get_llm uses base_url when api_base is not provided."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance = Mock()
            mock_chat_litellm.return_value = mock_llm_instance
            
            result = llm_manager.get_llm(
                model="test-model", 
                api_key="test-key",
                base_url="https://api.example.com"
            )
            
            assert result == mock_llm_instance
            mock_chat_litellm.assert_called_once_with(
                model="test-model", 
                api_key="test-key", 
                api_base="https://api.example.com"
            )

    def test_get_llm_different_params_create_different_instances(self, llm_manager):
        """Test that different parameters create different cached instances."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance1 = Mock()
            mock_llm_instance2 = Mock()
            mock_chat_litellm.side_effect = [mock_llm_instance1, mock_llm_instance2]
            
            # First instance
            result1 = llm_manager.get_llm(model="model1", api_key="key1")
            
            # Second instance with different params
            result2 = llm_manager.get_llm(model="model2", api_key="key2")
            
            assert result1 == mock_llm_instance1
            assert result2 == mock_llm_instance2
            assert result1 != result2
            assert mock_chat_litellm.call_count == 2

    def test_get_llm_logs_creation(self, llm_manager, mock_log_manager):
        """Test that LLM creation is properly logged."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance = Mock()
            mock_chat_litellm.return_value = mock_llm_instance
            
            llm_manager.get_llm(model="test-model", api_key="test-key")
            
            mock_log_manager.log_with_context.assert_called_with(
                "info", 
                "LLM instance created and cached.", 
                context={"params": {"model": "test-model", "api_key": "***"}}
            )

    def test_list_available_llms_empty(self, llm_manager):
        """Test list_available_llms returns empty list initially."""
        result = llm_manager.list_available_llms()
        assert result == []

    def test_list_available_llms_with_cached_instances(self, llm_manager):
        """Test list_available_llms returns cache keys of created instances."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_chat_litellm.return_value = Mock()
            
            # Create some LLM instances
            llm_manager.get_llm(model="model1", api_key="key1")
            llm_manager.get_llm(model="model2", api_key="key2")
            
            result = llm_manager.list_available_llms()
            
            # Should have 2 cache keys
            assert len(result) == 2
            assert all(isinstance(key, tuple) for key in result)

    def test_get_llm_cache_key_generation(self, llm_manager):
        """Test that cache keys are generated correctly for different parameter combinations."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_chat_litellm.return_value = Mock()
            
            # Create instances with different parameter combinations
            llm_manager.get_llm(model="model1", api_key="key1")
            llm_manager.get_llm(model="model1", api_key="key1", api_base="base1")
            llm_manager.get_llm(model="model2", api_key="key1")
            
            # Should have 3 different cache entries
            assert len(llm_manager._llms) == 3
            assert mock_chat_litellm.call_count == 3

    def test_get_llm_handles_none_api_key(self, llm_manager):
        """Test get_llm handles None API key correctly."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance = Mock()
            mock_chat_litellm.return_value = mock_llm_instance
            
            result = llm_manager.get_llm(model="test-model", api_key=None)
            
            assert result == mock_llm_instance
            mock_chat_litellm.assert_called_once_with(
                model="test-model", 
                api_key=None, 
                api_base=None
            )

    def test_get_llm_creation_failure_not_cached(self, llm_manager):
        """Test that failed LLM creation doesn't add to cache."""
        with patch.object(llm_manager_module, 'ChatLiteLLM') as mock_chat_litellm:
            mock_chat_litellm.side_effect = Exception("Creation failed")
            
            with pytest.raises(Exception, match="Creation failed"):
                llm_manager.get_llm(model="test-model", api_key="test-key")
            
            # Cache should be empty after failed creation
            assert len(llm_manager._llms) == 0