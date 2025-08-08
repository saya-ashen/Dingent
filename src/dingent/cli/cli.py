import os
import queue
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Annotated

import click
import typer
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.main import cookiecutter
from loguru import logger

from .context import CliContext

PROD_REPO_URL = "https://github.com/saya-ashen/Dingent.git"
DEV_REPO_URL = "/home/saya/Workspace/Dingent"

AVAILABLE_TEMPLATES = ["basic"]
IS_DEV_MODE = os.getenv("DINGENT_DEV")

REPO_URL = DEV_REPO_URL if IS_DEV_MODE else PROD_REPO_URL

app = typer.Typer(name="dingent")
assistants_app = typer.Typer(help="Manage the 'assistants' component and its plugins.")
app.add_typer(assistants_app, name="assistants")
assistants_plugin_app = typer.Typer(help="Manage plugins for the 'assistants' component.")
assistants_app.add_typer(assistants_plugin_app, name="plugin")


class EnvironmentInfo:
    """Detects and stores information about the user's environment."""

    def __init__(self):
        self.uv_path = shutil.which("uv")
        self.bun_path = shutil.which("bun")
        self.npm_path = shutil.which("npm")
        self.os_platform = sys.platform

    @property
    def is_uv_installed(self):
        """Check if 'uv' is available."""
        return self.uv_path is not None

    @property
    def frontend_installer(self):
        """Determines the preferred frontend package manager."""
        if self.bun_path:
            return "bun", [self.bun_path, "install"]
        if self.npm_path:
            return "npm", [self.npm_path, "install"]
        return None, None


class ProjectInitializer:
    """Handles the logic for the 'init' command."""

    def __init__(self, project_name, template, checkout, env_info):
        self.project_name = project_name
        self.template = template
        self.checkout = checkout
        self.env = env_info
        self.project_path = None

    def run(self):
        """Executes the entire project initialization workflow."""
        try:
            self._create_from_template()
            self._convert_sql_to_db()
            self._install_python_dependencies()
            self._install_frontend_dependencies()
            self._print_final_summary()
        except RepositoryNotFound:
            click.secho(f"\n❌ Error: Repository not found at {REPO_URL}", fg="red", bold=True)
            click.echo("Please check the URL and your network connection.")
            raise typer.Exit()
        except Exception as e:
            click.secho(f"\n❌ An unexpected error occurred: {e}", fg="red", bold=True)
            # Add more specific error handling or logging here if needed
            raise typer.Exit()

    def _create_from_template(self):
        """Uses Cookiecutter to scaffold the project."""
        click.secho(f"🚀 Initializing project from git repository: {REPO_URL}", fg="green")
        template_dir = f"templates/{self.template}"
        created_path = cookiecutter(
            REPO_URL,
            directory=template_dir,
            checkout=self.checkout,
            extra_context={"project_slug": self.project_name},
            output_dir=".",
        )
        self.project_path = Path(created_path)
        click.secho("\n✅ Project structure created successfully!", fg="green")

    def _convert_sql_to_db(self):
        """Finds .sql files and converts them to SQLite .db files."""
        click.secho("\n✨ Converting .sql files to .db databases...", fg="cyan")
        sql_dir = self.project_path / "assistants" / "data"
        if not sql_dir.is_dir():
            click.secho(f"⚠️ Warning: SQL data directory not found at '{sql_dir}'.", fg="yellow")
            return

        sql_files = sorted(sql_dir.glob("*.sql"))
        if not sql_files:
            click.secho(f"ℹ️ Info: No .sql files found in '{sql_dir}'.", fg="blue")
            return

        click.echo(f"  -> Found {len(sql_files)} SQL file(s).")
        success_count, error_count = 0, 0
        for sql_file in sql_files:
            db_path = sql_file.with_suffix(".db")
            click.echo(f"    - Converting '{sql_file.name}' -> '{db_path.name}'")
            try:
                with sqlite3.connect(db_path) as conn:
                    with open(sql_file, encoding="utf-8") as f:
                        conn.cursor().executescript(f.read())
                success_count += 1
            except sqlite3.Error as e:
                click.secho(f"      ❌ Error: {e}", fg="red")
                if db_path.exists():
                    db_path.unlink()
                error_count += 1

        summary_color = "green" if error_count == 0 else "yellow"
        click.secho(f"\n✅ Conversion complete. {success_count} succeeded, {error_count} failed.", fg=summary_color)

    def _install_python_dependencies(self):
        """Installs dependencies for Python subdirectories using 'uv'."""
        click.secho("\n📦 Installing Python dependencies with 'uv sync'...", fg="cyan")
        if not self.env.is_uv_installed:
            click.secho("⚠️ Warning: 'uv' not found. Skipping dependency installation.", fg="yellow")
            click.echo("   Please install uv (https://github.com/astral-sh/uv) and run 'uv sync' manually.")
            return

        install_errors = False
        for subdir_name in ["assistants", "backend"]:
            target_dir = self.project_path / subdir_name
            if target_dir.is_dir() and (target_dir / "pyproject.toml").exists():
                click.echo(f"  -> Running 'uv sync' in '{subdir_name}'...")
                try:
                    # Using 'uv venv' and 'uv sync' ensures a virtual environment is created and used
                    subprocess.run([self.env.uv_path, "venv"], cwd=str(target_dir), check=True, capture_output=True)
                    subprocess.run([self.env.uv_path, "sync"], cwd=str(target_dir), check=True, capture_output=True, text=True)
                    click.secho(f"    ✅ Successfully installed dependencies in '{subdir_name}'.", fg="green")
                except subprocess.CalledProcessError as e:
                    install_errors = True
                    click.secho(f"    ❌ Error installing in '{subdir_name}'.", fg="red")
                    click.echo(e.stderr, err=True)
            else:
                click.secho(f"  -> Skipping '{subdir_name}', 'pyproject.toml' not found.", fg="blue")

        if install_errors:
            click.secho("\n⚠️ Some Python dependencies failed to install.", fg="yellow")
        else:
            click.secho("\n✅ All Python dependencies installed!", fg="green")

    def _install_frontend_dependencies(self):
        """Installs dependencies for the frontend using bun or npm."""
        click.secho("\n🌐 Installing frontend dependencies...", fg="cyan")
        tool_name, install_cmd = self.env.frontend_installer
        if not tool_name:
            click.secho("⚠️ Warning: 'bun' or 'npm' not found. Skipping.", fg="yellow")
            return

        frontend_dir = self.project_path / "frontend"
        if frontend_dir.is_dir() and (frontend_dir / "package.json").exists():
            click.echo(f"  -> Running '{' '.join(install_cmd)}'...")
            try:
                subprocess.run(install_cmd, cwd=str(frontend_dir), check=True, capture_output=True, text=True)
                click.secho(f"    ✅ Successfully installed with {tool_name}.", fg="green")
            except subprocess.CalledProcessError as e:
                click.secho(f"    ❌ Error installing with {tool_name}.", fg="red")
                click.echo(e.stderr, err=True)

    def _print_final_summary(self):
        """Prints the final success message and next steps."""
        final_project_name = self.project_path.name
        click.secho("\n🎉 Project initialized successfully!", fg="green", bold=True)
        click.echo("\nNext steps:")
        click.echo(f"  1. Navigate to your project: cd {final_project_name}")
        click.echo("  2. Start all services: dingent run")


class ServiceRunner:
    """Handles the logic for the 'run' command."""

    def __init__(self, env_info: EnvironmentInfo, cli_ctx: CliContext):
        self.env = env_info
        self.services = {
            "assistants": {"command": ["python", "main.py"], "cwd": cli_ctx.assistants_path, "color": "blue"},
            "backend": {"command": ["langgraph", "dev", "--no-browser"], "cwd": cli_ctx.backend_path, "color": "magenta"},
            "frontend": {"command": [f"{env_info.frontend_installer[0]}", "dev"], "cwd": cli_ctx.frontend_path, "color": "yellow"},
        }
        self.processes = []

    def run(self):
        """Starts, monitors, and shuts down all services."""
        try:
            self._validate_and_prepare_services()
            self._start_services()
            self._monitor_services()
        except (KeyboardInterrupt, RuntimeError) as e:
            if isinstance(e, RuntimeError):
                click.secho(f"\nReason: {e}", fg="red")
        finally:
            self._shutdown_services()

    def _validate_and_prepare_services(self):
        """Validates executables and prepares commands using 'uv run'."""
        click.secho("🔎 Resolving service executables...", fg="cyan")

        # 1. Check for 'uv' command, required for Python services
        if not shutil.which("uv"):
            click.secho("❌ Error: 'uv' command not found.", fg="red")
            click.echo("   Please install uv: https://github.com/astral-sh/uv")
            raise typer.Exit()
        click.echo("  -> Found 'uv' executable.")

        # 2. Update Python service commands to use 'uv run'
        # This is simpler and more robust than manually finding venv executables.
        # 'uv run' will automatically detect and use the .venv in the service's 'cwd'.
        for name in ["assistants", "backend"]:
            original_command = self.services[name]["command"]
            self.services[name]["command"] = ["uv", "run", "--"] + original_command
            click.echo(f"  -> Prepared '{name}' command: {' '.join(self.services[name]['command'])}")

        # 3. Check for 'bun' command for the frontend service
        frontend_cmd = self.services["frontend"]["command"][0]
        if not shutil.which(frontend_cmd):
            click.secho(f"❌ Error: Command '{frontend_cmd}' not found.", fg="red")
            click.secho("   Please ensure Bun is installed and in your system's PATH.", fg="red")
            raise typer.Exit()
        click.echo(f"  -> Found '{frontend_cmd}' executable.")

    def _start_services(self):
        """Starts all services as subprocesses and sets up log streaming."""
        click.secho("\n🚀 Starting all development services...", fg="cyan", bold=True)
        log_queue = queue.Queue()

        for name, service in self.services.items():
            try:
                proc = subprocess.Popen(service["command"], cwd=service["cwd"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1)
            except FileNotFoundError:
                click.secho(f"❌ Error: directory '{service['cwd']}' not found.", fg="red")
                click.secho("Please ensure that you are in the correct project directory.", fg="red")
                raise typer.Exit()
            self.processes.append((name, proc))

            thread = threading.Thread(target=self._stream_output, args=(name, proc, log_queue))
            thread.daemon = True
            thread.start()
            click.secho(f"✅ {name.capitalize()} service started (PID: {proc.pid}).", fg="green")

        self.log_queue = log_queue

    def _monitor_services(self):
        """Monitors running services and prints their logs."""
        click.echo("\nGiving services a moment to warm up...")
        time.sleep(3)
        click.secho("🌐 Opening http://localhost:3000 in your browser.", bold=True)
        webbrowser.open_new_tab("http://localhost:3000")
        click.secho("\n--- Real-time Logs (Press Ctrl+C to stop) ---", bold=True)

        while self.processes:
            # Check for terminated processes
            for i in range(len(self.processes) - 1, -1, -1):
                name, proc = self.processes[i]
                if proc.poll() is not None:
                    self._flush_log_queue()
                    click.secho(f"\n❌ Service '{name}' has terminated unexpectedly.", fg="red", bold=True)
                    raise RuntimeError(f"Service '{name}' exited with code {proc.returncode}.")

            # Print logs from the queue
            while not self.log_queue.empty():
                self._print_log_line()
            time.sleep(0.1)

    def _shutdown_services(self):
        """Terminates all running child processes."""
        click.secho("\n\n🛑 Shutting down all services...", fg="yellow", bold=True)
        for name, proc in self.processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                click.secho(f"🔌 {name.capitalize()} service stopped.", fg="blue")
        click.secho("\n✨ All services have been shut down. Goodbye!", fg="green")

    def _stream_output(self, name, process, log_queue):
        """Reads a process's stdout and puts lines into the queue."""
        try:
            for line in iter(process.stdout.readline, ""):
                log_queue.put((name, line))
            process.stdout.close()
        except UnicodeDecodeError as e:
            # FIXME: Handle decoding errors gracefully
            click.secho(f"❌ Error decoding output from {name} service: {e}", fg="red")

    def _print_log_line(self):
        """Gets and prints a single log line from the queue if available."""
        try:
            name, line = self.log_queue.get_nowait()
            prefix = click.style(f"[{name.upper():^8}]", fg=self.services[name]["color"])
            click.echo(f"{prefix} {line.strip()}")
        except queue.Empty:
            pass

    def _flush_log_queue(self):
        """Prints all remaining logs in the queue."""
        while not self.log_queue.empty():
            self._print_log_line()


@click.group()
def cli():
    """A CLI for the Dingent framework."""
    pass


@app.callback()
def main(ctx: typer.Context):
    """
    Dingent Agent Framework CLI
    """
    # 1. 创建上下文对象
    cli_context = CliContext()

    # 2. 检查是否在项目目录中
    if not cli_context.is_in_project:
        pass

    # 3. 将我们的上下文对象挂载到 Typer 的上下文中
    ctx.obj = cli_context


@app.command("init")
def init(
    project_name: Annotated[str, typer.Argument()],
    template: Annotated[str, typer.Option(help="The template used to create the project.")] = "basic",
    checkout: Annotated[str, typer.Option(help="The branch, tag, or commit to checkout.")] = "main",
):
    """Creates a new agent project from a template."""
    env_info = EnvironmentInfo()
    initializer = ProjectInitializer(project_name, template, checkout, env_info)
    initializer.run()


@app.command("run")
def run(
    ctx: typer.Context,
):
    """Runs the Assistants, Backend, and Frontend services concurrently."""
    cli_ctx: CliContext = ctx.obj
    env_info = EnvironmentInfo()
    runner = ServiceRunner(env_info, cli_ctx)
    runner.run()


@assistants_app.command("run")
def assistants_run():
    raise NotImplementedError("The 'assistants run' command is not yet implemented.")


@assistants_plugin_app.command("list")
def assistants_plugin_list(ctx: typer.Context):
    cli_ctx: CliContext = ctx.obj
    if not cli_ctx.is_in_project:
        logger.error("❌ Error: Not inside a dingent project. (Cannot find 'dingent.toml')")
        raise typer.Exit(code=1)
    if cli_ctx.assistants_plugin_manager:
        plugins = cli_ctx.assistants_plugin_manager.get_registered_plugins()
        print("All registered plugins:\n", "\n".join(list(plugins.keys())))
    else:
        logger.error("❌ Error: Plugin manager not initialized.")


def install_dependencies_for_plugin(cli_ctx, env, plugin_name: str):
    if not cli_ctx.is_in_project:
        logger.error("❌ Error: Not inside a dingent project. (Cannot find 'dingent.toml')")
        raise typer.Exit(code=1)
    if not env.is_uv_installed:
        logger.error("❌ Error: 'uv' is not installed. Please install it first.")
        raise typer.Exit(code=1)
    if cli_ctx.assistants_plugin_manager:
        plugins = cli_ctx.assistants_plugin_manager.get_registered_plugins()
        plugin = plugins.get(plugin_name)
        if not plugin:
            logger.error(f"❌ Error: Plugin '{plugin_name}' not found.")
            raise typer.Exit(code=1)
        dependecies = plugin.get("dependencies", [])
        if cli_ctx.assistants_path is not None:
            result = subprocess.run([env.uv_path, "add", "--optional", f"plugin-{plugin_name}"] + dependecies, cwd=cli_ctx.assistants_path, check=True, capture_output=True)
            print("依赖安装成功！")
            print("--- uv 输出 ---")
            print(result.stdout.decode())
    else:
        logger.error("❌ Error: Plugin manager not initialized.")


@assistants_plugin_app.command("sync")
def assistants_plugin_install(ctx: typer.Context, plugin_name: Annotated[str | None, typer.Argument()] = None):
    """
    Install dependencies for a specific plugin.
    """
    cli_ctx: CliContext = ctx.obj
    env = EnvironmentInfo()
    if plugin_name:
        install_dependencies_for_plugin(cli_ctx, env, plugin_name)
    else:
        if not cli_ctx.assistants_plugin_manager:
            raise typer.Exit()
        for plugin in cli_ctx.assistants_plugin_manager.get_registered_plugins().values():
            install_dependencies_for_plugin(cli_ctx, env, plugin.get("name"))
