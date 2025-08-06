import subprocess
from unittest.mock import call

import pytest
from click.testing import CliRunner

from dingent.cli import cli


@pytest.fixture
def runner():
    """
    Provides a CliRunner instance for invoking commands.
    """
    return CliRunner()


def test_run_command_starts_services(runner, mocker, tmp_path):
    """
    Test that the 'run' command correctly starts all services.
    """
    mocker.patch("os.chdir", lambda path: None)

    (tmp_path / "frontend").mkdir()

    mock_popen = mocker.patch("subprocess.Popen")
    mocker.patch("shutil.which", return_value="/fake/path/to/bun")
    mocker.patch("webbrowser.open_new_tab")
    mocker.patch("time.sleep")
    mocker.patch("dingent.cli.ServiceRunner._monitor_services", side_effect=KeyboardInterrupt)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["run"])

    assert "🚀 Starting all development services..." in result.output
    assert "🛑 Shutting down all services..." in result.output

    expected_mcp_cmd = ["uv", "run", "--", "python", "main.py"]
    expected_backend_cmd = ["uv", "run", "--", "langgraph", "dev", "--no-browser"]
    expected_frontend_cmd = ["bun", "dev"]

    popen_calls = [
        call(expected_mcp_cmd, cwd="mcp", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1),
        call(expected_backend_cmd, cwd="backend", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1),
        call(expected_frontend_cmd, cwd="frontend", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1),
    ]
    mock_popen.assert_has_calls(popen_calls, any_order=True)
    assert mock_popen.call_count == 3


def test_run_command_starts_services_without_bun(runner, mocker, tmp_path):
    mocker.patch("os.chdir", lambda path: None)

    (tmp_path / "frontend").mkdir()

    def shutil_which(name: str):
        if name == "npm":
            return "/fake/path/to/npm"
        elif name == "uv":
            return "/fake/path/to/uv"
        else:
            return None

    mock_popen = mocker.patch("subprocess.Popen")
    mocker.patch("shutil.which", side_effect=shutil_which)
    mocker.patch("webbrowser.open_new_tab")
    mocker.patch("time.sleep")
    mocker.patch("dingent.cli.ServiceRunner._monitor_services", side_effect=KeyboardInterrupt)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["run"])

    assert "🚀 Starting all development services..." in result.output
    assert "🛑 Shutting down all services..." in result.output

    expected_mcp_cmd = ["uv", "run", "--", "python", "main.py"]
    expected_backend_cmd = ["uv", "run", "--", "langgraph", "dev", "--no-browser"]
    expected_frontend_cmd = ["npm", "dev"]

    popen_calls = [
        call(expected_mcp_cmd, cwd="mcp", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1),
        call(expected_backend_cmd, cwd="backend", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1),
        call(expected_frontend_cmd, cwd="frontend", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1),
    ]
    mock_popen.assert_has_calls(popen_calls, any_order=True)
    assert mock_popen.call_count == 3
