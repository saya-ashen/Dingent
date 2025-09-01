"""
Tests for LLMManager - core LLM instance management and caching.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import SecretStr

from dingent.core.llm_manager import LLMManager
from dingent.core.log_manager import LogManager


class TestLLMManager:
    """Test suite for LLMManager."""

    @pytest.fixture
    def llm_manager(self, mock_log_manager):
        """Create an LLMManager instance for testing."""
        return LLMManager(mock_log_manager)

    def test_llm_manager_initialization(self, mock_log_manager):
        """Test LLMManager initializes correctly."""
        llm_manager = LLMManager(mock_log_manager)
        
        assert llm_manager._llms == {}
        assert llm_manager._log_manager == mock_log_manager

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_creates_and_caches_instance(self, mock_chat_litellm, llm_manager):
        """Test that get_llm creates and caches LLM instances."""
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

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_with_secret_str_api_key(self, mock_chat_litellm, llm_manager):
        """Test get_llm handles SecretStr API keys correctly."""
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

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_with_api_base(self, mock_chat_litellm, llm_manager):
        """Test get_llm handles api_base parameter."""
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

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_with_base_url_fallback(self, mock_chat_litellm, llm_manager):
        """Test get_llm uses base_url when api_base is not provided."""
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

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_different_params_create_different_instances(self, mock_chat_litellm, llm_manager):
        """Test that different parameters create different cached instances."""
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
        with patch('dingent.core.llm_manager.ChatLiteLLM') as mock_chat_litellm:
            mock_llm_instance = Mock()
            mock_chat_litellm.return_value = mock_llm_instance
            
            llm_manager.get_llm(model="test-model", api_key="test-key")
            
            mock_log_manager.log_with_context.assert_called_with(
                "info", 
                "LLM instance created and cached.", 
                context={"params": {"model": "test-model", "api_key": "***", "api_base": None}}
            )

    def test_list_available_llms_empty(self, llm_manager):
        """Test list_available_llms returns empty list initially."""
        result = llm_manager.list_available_llms()
        assert result == []

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_list_available_llms_with_cached_instances(self, mock_chat_litellm, llm_manager):
        """Test list_available_llms returns cache keys of created instances."""
        mock_chat_litellm.return_value = Mock()
        
        # Create some LLM instances
        llm_manager.get_llm(model="model1", api_key="key1")
        llm_manager.get_llm(model="model2", api_key="key2")
        
        result = llm_manager.list_available_llms()
        
        # Should have 2 cache keys
        assert len(result) == 2
        assert all(isinstance(key, tuple) for key in result)

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_cache_key_generation(self, mock_chat_litellm, llm_manager):
        """Test that cache keys are generated correctly for different parameter combinations."""
        mock_chat_litellm.return_value = Mock()
        
        # Create instances with different parameter combinations
        llm_manager.get_llm(model="model1", api_key="key1")
        llm_manager.get_llm(model="model1", api_key="key1", api_base="base1")
        llm_manager.get_llm(model="model2", api_key="key1")
        
        # Should have 3 different cache entries
        assert len(llm_manager._llms) == 3
        assert mock_chat_litellm.call_count == 3

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_handles_none_api_key(self, mock_chat_litellm, llm_manager):
        """Test get_llm handles None API key correctly."""
        mock_llm_instance = Mock()
        mock_chat_litellm.return_value = mock_llm_instance
        
        result = llm_manager.get_llm(model="test-model", api_key=None)
        
        assert result == mock_llm_instance
        mock_chat_litellm.assert_called_once_with(
            model="test-model", 
            api_key=None, 
            api_base=None
        )

    @patch('dingent.core.llm_manager.ChatLiteLLM')
    def test_get_llm_creation_failure_not_cached(self, mock_chat_litellm, llm_manager):
        """Test that failed LLM creation doesn't add to cache."""
        mock_chat_litellm.side_effect = Exception("Creation failed")
        
        with pytest.raises(Exception, match="Creation failed"):
            llm_manager.get_llm(model="test-model", api_key="test-key")
        
        # Cache should be empty after failed creation
        assert len(llm_manager._llms) == 0