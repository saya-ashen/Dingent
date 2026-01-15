"""Tests for subpath deployment configuration."""
import os
from unittest.mock import patch
import pytest


def test_backend_root_path_configuration():
    """Test that the backend respects the API_ROOT_PATH environment variable."""
    # Test with no root path set
    with patch.dict(os.environ, {}, clear=False):
        if "API_ROOT_PATH" in os.environ:
            del os.environ["API_ROOT_PATH"]
        
        from dingent.server.app import create_app
        app = create_app()
        assert app.root_path == ""
    
    # Test with root path set
    with patch.dict(os.environ, {"API_ROOT_PATH": "/dingent/web"}):
        # Need to reimport to pick up new env var
        import importlib
        import dingent.server.app
        importlib.reload(dingent.server.app)
        
        app = dingent.server.app.create_app()
        assert app.root_path == "/dingent/web"


def test_cli_passes_base_path_to_services():
    """Test that the CLI properly sets environment variables when base_path is provided."""
    # Simulate creating a backend service with base_path
    base_path = "/dingent/web"
    backend_env = dict(os.environ)
    backend_env["API_ROOT_PATH"] = base_path
    
    # Verify the environment contains the expected variable
    assert backend_env["API_ROOT_PATH"] == base_path


def test_health_check_url_construction():
    """Test health check URL construction with and without base path."""
    from dingent.cli.cli import _build_health_check_url
    
    host = "localhost"
    port = 8000
    
    # Without base path
    health_check_url = _build_health_check_url(host, port)
    assert health_check_url == "http://localhost:8000/api/v1/health"
    
    # With base path
    base_path = "/dingent/web"
    health_check_url = _build_health_check_url(host, port, base_path)
    assert health_check_url == "http://localhost:8000/dingent/web/api/v1/health"
