from unittest.mock import MagicMock, call

import pytest
from click.testing import CliRunner
from cookiecutter.exceptions import RepositoryNotFound

from dingent.cli import cli

REPO_URL = "https://fake.repo/dingent.git"


@pytest.fixture
def runner():
    """
    Provides a CliRunner instance for invoking commands.
    """
    return CliRunner()


def test_init_command_success(runner: CliRunner, mocker, tmp_path):
    """
    Test the 'init' command's success path when all external tools are available.
    """
    mocker.patch("dingent.cli.REPO_URL", REPO_URL)
    mocker.patch("shutil.which", return_value="/fake/path/to/tool")

    mock_cookiecutter = mocker.patch("dingent.cli.cookiecutter", return_value=str(tmp_path / "my-awesome-agent"))

    mock_subprocess_run = mocker.patch("subprocess.run", return_value=MagicMock(returncode=0))

    mocker.patch("sqlite3.connect")

    project_path = tmp_path / "my-awesome-agent"
    sql_dir = project_path / "mcp" / "data"
    sql_dir.mkdir(parents=True, exist_ok=True)
    (sql_dir / "sample.sql").write_text("CREATE TABLE test (id INT);")

    (project_path / "mcp" / "pyproject.toml").touch()
    (project_path / "backend").mkdir()
    (project_path / "backend" / "pyproject.toml").touch()
    (project_path / "frontend").mkdir()
    (project_path / "frontend" / "package.json").touch()

    result = runner.invoke(cli, ["init", "my-awesome-agent"], input="y\n")

    assert result.exit_code == 0, f"CLI exited with error: {result.output}"
    assert "🎉 Project initialized successfully!" in result.output

    mock_cookiecutter.assert_called_once_with(
        REPO_URL,
        directory="templates/basic",
        checkout=None,
        extra_context={"project_slug": "my-awesome-agent"},
        output_dir=".",
    )

    uv_calls = [
        call([mocker.ANY, "venv"], cwd=str(project_path / "mcp"), check=True, capture_output=True),
        call([mocker.ANY, "sync"], cwd=str(project_path / "mcp"), check=True, capture_output=True, text=True),
        call([mocker.ANY, "venv"], cwd=str(project_path / "backend"), check=True, capture_output=True),
        call([mocker.ANY, "sync"], cwd=str(project_path / "backend"), check=True, capture_output=True, text=True),
    ]
    mock_subprocess_run.assert_has_calls(uv_calls, any_order=True)

    mock_subprocess_run.assert_any_call([mocker.ANY, "install"], cwd=str(project_path / "frontend"), check=True, capture_output=True, text=True)


def test_init_command_uv_not_installed(runner: CliRunner, mocker, tmp_path):
    """
    Test the 'init' command's behavior when 'uv' is not installed.
    """
    mocker.patch("dingent.cli.REPO_URL", REPO_URL)
    mocker.patch("shutil.which", return_value=None)
    mocker.patch("cookiecutter.main.cookiecutter", return_value=str(tmp_path / "my-agent"))
    mocker.patch("subprocess.run")
    mock_subprocess_run = mocker.patch("subprocess.run", return_value=MagicMock(returncode=0))
    mocker.patch("dingent.cli.cookiecutter", return_value=str(tmp_path / "my-awesome-agent"))

    result = runner.invoke(cli, ["init", "my-agent"], input="y\n", catch_exceptions=True)

    assert result.exit_code == 0
    assert "Warning: 'uv' not found. Skipping dependency installation." in result.output
    assert "Warning: 'bun' or 'npm' not found. Skipping." in result.output
    mock_subprocess_run.assert_not_called()


def test_init_command_repo_not_found(runner, mocker):
    """
    Test that the command fails gracefully with an appropriate error message when the repository is not found.
    """
    mocker.patch("dingent.cli.REPO_URL", REPO_URL)
    mocker.patch("dingent.cli.cookiecutter", side_effect=RepositoryNotFound("Repo not found"))

    result = runner.invoke(cli, ["init", "basic"], input="y\ny\ny\ny\ny\ny\ny\n")

    assert result.exit_code == 1
    assert f"Error: Repository not found at {REPO_URL}" in result.output
