# tests/conftest.py
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """Creates a temporary project root directory for testing."""
    (tmp_path / "config").mkdir()
    (tmp_path / "plugins").mkdir()
    return tmp_path


@pytest.fixture
def mock_log_manager():
    """Provides a mock LogManager."""
    logger = Mock()
    logger.log_with_context = Mock()
    return logger
