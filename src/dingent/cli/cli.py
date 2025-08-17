import os
import queue
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from importlib import resources
from pathlib import Path
from typing import Annotated

import typer
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.main import cookiecutter
from loguru import logger
from rich import print
from rich.text import Text

from .context import CliContext

PROD_REPO_URL = "https://github.com/saya-ashen/Dingent.git"
DEV_REPO_URL = "/home/saya/Workspace/Dingent"

AVAILABLE_TEMPLATES = ["basic"]
IS_DEV_MODE = os.getenv("DINGENT_DEV")

REPO_URL = DEV_REPO_URL if IS_DEV_MODE else PROD_REPO_URL

app = typer.Typer(name="dingent")
plugin_app = typer.Typer(help="Manage Plugins")
app.add_typer(plugin_app, name="plugin")
assistant_app = typer.Typer(help="Manage Assistatns")
app.add_typer(assistant_app, name="assistant")


class EnvironmentInfo:
    """Detects and stores information about the user's environment."""

    def __init__(self):
        self.uv_path = shutil.which("uv")
        self.bun_path = shutil.which("bun")
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
            print(f"[bold red]\n❌ Error: Repository not found at {REPO_URL}[/bold red]")
            print("[bold red]\nPlease check the URL and your network connection.[/bold red]")
            raise typer.Exit()
        except Exception as e:
            print(f"[bold red]\nAn unexpected error occurred: {e}[/bold red]")
            raise typer.Exit()

    def _create_from_template(self):
        """Uses Cookiecutter to scaffold the project."""
        print(f"[bold green]🚀 Initializing project from git repository: {REPO_URL}[/bold green]")
        template_dir = f"templates/{self.template}"
        created_path = cookiecutter(
            REPO_URL,
            directory=template_dir,
            checkout=self.checkout,
            extra_context={"project_slug": self.project_name},
            output_dir=".",
        )
        self.project_path = Path(created_path)
        print(f"[bold green]✅ Project created at {self.project_path}[/bold green]")

    def _convert_sql_to_db(self):
        """Finds .sql files and converts them to SQLite .db files."""
        print("[bold green]\n✨ Converting .sql files to .db databases...[/bold green]")
        sql_dir = self.project_path / "backend" / "data"
        if not sql_dir.is_dir():
            print(f"[bold yellow]\n⚠️ Warning: SQL data directory not found at '{sql_dir}'.[/bold yellow]")
            return

        sql_files = sorted(sql_dir.glob("*.sql"))
        if not sql_files:
            print(f"[bold blue]\nℹ️ Info: No .sql files found in '{sql_dir}'.[/bold blue]")
            return

        print(f"[bold green]  -> Found {len(sql_files)} SQL file(s).[/bold green]")
        success_count, error_count = 0, 0
        for sql_file in sql_files:
            db_path = sql_file.with_suffix(".db")
            print(f"    - Converting '{sql_file.name}' -> '{db_path.name}'")
            try:
                with sqlite3.connect(db_path) as conn:
                    with open(sql_file, encoding="utf-8") as f:
                        conn.cursor().executescript(f.read())
                success_count += 1
            except sqlite3.Error as e:
                print(f"[bold red]      ❌ Error: {e}[/bold red]")
                if db_path.exists():
                    db_path.unlink()
                error_count += 1

        summary_color = "green" if error_count == 0 else "yellow"
        print(f"[{summary_color}]\n✅ Conversion complete. {success_count} succeeded, {error_count} failed.[/{summary_color}]")

    def _install_python_dependencies(self):
        """Installs dependencies for Python subdirectories using 'uv'."""
        print("\n📦 Installing Python dependencies with 'uv sync'...")
        if not self.env.is_uv_installed:
            print("⚠️ Warning: 'uv' not found. Skipping dependency installation.")
            print("   Please install uv (https://github.com/astral-sh/uv) and run 'uv sync' manually.")
            return

        install_errors = False
        for subdir_name in ["backend"]:
            target_dir = self.project_path / subdir_name
            if target_dir.is_dir() and (target_dir / "pyproject.toml").exists():
                print(f"  -> Running 'uv sync' in '{subdir_name}'...")
                try:
                    subprocess.run([self.env.uv_path, "venv"], cwd=str(target_dir), check=True, capture_output=True)
                    subprocess.run([self.env.uv_path, "sync"], cwd=str(target_dir), check=True, capture_output=True, text=True)
                    print(f"[green]    ✅ Successfully installed dependencies in '{subdir_name}'.[/green]")
                except subprocess.CalledProcessError as e:
                    install_errors = True
                    print(f"[bold red]    ❌ Error installing in '{subdir_name}'.[/bold red]")
                    if e.stderr:
                        print(f"[bold red]{e.stderr}[/bold red]")
            else:
                print(f"  -> Skipping '{subdir_name}', 'pyproject.toml' not found.")

        if install_errors:
            print("[bold yellow]\n⚠️ Some Python dependencies failed to install.[/bold yellow]")
        else:
            print("[bold green]\n✅ All Python dependencies installed![/bold green]")

    def _install_frontend_dependencies(self):
        """Installs dependencies for the frontend using bun."""
        print("[bold cyan]\n🌐 Installing frontend dependencies...[/bold cyan]")
        tool_name, install_cmd = self.env.frontend_installer
        if not tool_name:
            print("[bold yellow]⚠️ Warning: 'bun' not found. Skipping.[/bold yellow]")
            return

        frontend_dir = self.project_path / "frontend"
        if frontend_dir.is_dir() and (frontend_dir / "package.json").exists():
            print(f"  -> Running '{' '.join(install_cmd)}'...")
            try:
                subprocess.run(install_cmd, cwd=str(frontend_dir), check=True, capture_output=True, text=True)
                print(f"[bold green]    ✅ Successfully installed with {tool_name}.[/bold green]")
            except subprocess.CalledProcessError as e:
                print(f"[bold red]    ❌ Error installing with {tool_name}.[/bold red]")
                if e.stderr:
                    print(f"[bold red]{e.stderr}[/bold red]")

    def _print_final_summary(self):
        """Prints the final success message and next steps."""
        final_project_name = self.project_path.name
        print("[bold green]\n🎉 Project initialized successfully![/bold green]")
        print("\nNext steps:")
        print(f"  1. Navigate to your project: cd {final_project_name}")
        print("  2. Start all services: uvx dingent run")


class ServiceRunner:
    """Handles the logic for the 'run' command."""

    def __init__(self, env_info: EnvironmentInfo, cli_ctx: CliContext):
        self.env = env_info
        with resources.path("dingent.dashboard", "app.py") as frontend_file_path:
            script_full_path = str(frontend_file_path.as_posix())
            self.services = {
                "backend": {
                    "command": ["langgraph", "dev", "--no-browser", "--allow-blocking", "--port", str(cli_ctx.backend_port)],
                    "cwd": cli_ctx.backend_path,
                    "color": "magenta",
                },
                "frontend": {
                    "command": ["bun", "dev", "--port", str(cli_ctx.frontend_port)],
                    "env": {"DING_BACKEND_URL": f"http://127.0.0.1:{cli_ctx.backend_port}"},
                    "cwd": cli_ctx.frontend_path,
                    "color": "yellow",
                },
                "dashboard": {
                    "command": ["streamlit", "run", script_full_path, "--server.port", str(cli_ctx.dashboard_port)],
                    "env": {"DING_BACKEND_ADMIN_URL": f"http://127.0.0.1:{cli_ctx.backend_port}"},
                    "cwd": cli_ctx.backend_path,
                    "color": "blue",
                },
            }
        self.processes = []
        self.log_queue = queue.Queue()
        self._browser_opened = False

    def run(self):
        """Starts, monitors, and shuts down all services."""
        try:
            self._validate_and_prepare_services()
            self._start_services()
            self._monitor_services()
        except (KeyboardInterrupt, RuntimeError) as e:
            if isinstance(e, RuntimeError):
                print("[bold red]\nAborting operation due to a critical error.[/bold red]")
        finally:
            self._shutdown_services()

    def _validate_and_prepare_services(self):
        """Validates executables, converts them to absolute paths, and prepares commands."""
        print("[bold cyan]🔎 Resolving service executables to absolute paths...[/bold cyan]")

        # 1. Find and store the absolute path for the 'uv' command.
        uv_path = shutil.which("uv")
        if not uv_path:
            print("[bold red]❌ Error: 'uv' command not found.[/bold red]")
            print("   Please install uv: https://github.com/astral-sh/uv")
            raise RuntimeError("'uv' is not installed.")
        print(f"   -> Found 'uv' executable at: {uv_path}")

        # 2. Update Python-based service commands to use 'uv run'
        for name in ["backend", "dashboard"]:
            original_command = self.services[name]["command"]
            self.services[name]["command"] = [uv_path, "run", "--"] + original_command
            print(f"   -> Prepared '{name}' command: {' '.join(self.services[name]['command'])}")

        # 3. Resolve the frontend executable (bun) to an absolute path
        frontend_exe_name = self.services["frontend"]["command"][0]
        frontend_exe_path = shutil.which(frontend_exe_name)
        if not frontend_exe_path:
            print(f"[bold red]❌ Error: Command '{frontend_exe_name}' not found.[/bold red]")
            print("   Please ensure Bun is installed and in your system's PATH.")
            raise RuntimeError(f"Frontend executable '{frontend_exe_name}' not found.")
        print(f"   -> Found '{frontend_exe_name}' executable at: {frontend_exe_path}")

        self.services["frontend"]["command"][0] = frontend_exe_path
        print(f"   -> Prepared 'frontend' command: {' '.join(self.services['frontend']['command'])}")

    def _start_services(self):
        """Starts all services as subprocesses and sets up log streaming."""
        print("\n🚀 Starting all development services...")
        current_env = os.environ.copy()

        for name, service in self.services.items():
            command = service["command"]
            cwd = Path(service["cwd"])
            env = service.get("env", {})

            if not cwd.is_dir():
                print(f"[bold red]❌ Error: Working directory for '{name}' service not found.[/bold red]")
                print(f"   Directory: {cwd}")
                print("   Please ensure you are in the correct project root.")
                raise RuntimeError(f"Directory not found for {name} service.")

            try:
                updated_env = {**current_env, **env}

                popen_kwargs = {
                    "cwd": cwd,
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.STDOUT,
                    "env": updated_env,
                    "text": True,
                    "bufsize": 1,
                    "errors": "replace",
                }

                # Create a new process group/session for each service so we can terminate the whole tree
                if os.name == "posix":
                    popen_kwargs["start_new_session"] = True  # setsid()
                else:
                    # Windows: new process group to allow CTRL_BREAK_EVENT
                    popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

                proc = subprocess.Popen(command, **popen_kwargs)  # noqa: S603

            except FileNotFoundError:
                print(f"[bold red]❌ Fatal Error: Executable '{command[0]}' for the '{name}' service not found.[/bold red]")
                print(f"   Full Command: {' '.join(command)}")
                print(f"   Working Dir:  {cwd}")
                print("\n   [bold yellow]Troubleshooting Steps:[/bold yellow]")
                if name in ["backend", "dashboard"]:
                    print(f"    1. 'uv' was found, but it failed to run the service's command ('{command[3]}').")
                    print("    2. Make sure the virtual environment is correctly set up.")
                    print(f"    3. Try running 'uv sync' manually in the '{cwd}' directory.")
                else:
                    print(f"    1. Ensure '{command[0]}' is installed globally and available in your system's PATH.")
                    print(f"    2. Try running the command manually: cd {cwd} && {' '.join(command)}")
                raise RuntimeError(f"Executable not found for {name} service.")

            self.processes.append((name, proc))
            thread = threading.Thread(target=self._stream_output, args=(name, proc, self.log_queue), daemon=True)
            thread.start()
            print(f"[bold green]✅ {name.capitalize()} service started (PID: {proc.pid}).[/bold green]")

    def _monitor_services(self):
        """Monitors running services and prints their logs."""
        print("\nGiving services a moment to warm up...")
        time.sleep(3)

        print("\n--- Real-time Logs (Press Ctrl+C to stop) ---")

        while self.processes:
            # Check for terminated processes
            for i in range(len(self.processes) - 1, -1, -1):
                name, proc = self.processes[i]
                if proc.poll() is not None:
                    self._flush_log_queue()
                    print(f"\n[bold red]❌ Service '{name}' has terminated unexpectedly.[/bold red]")
                    raise RuntimeError(f"Service '{name}' exited with code {proc.returncode}.")

            # Print logs from the queue
            self._flush_log_queue()
            time.sleep(0.1)

    def _shutdown_services(self):
        """Terminates all running child processes (entire process groups)."""
        print("\n[bold yellow]🛑 Shutting down all services...[/bold yellow]")
        if not self.processes:
            print("   No services were running.")
            return

        for name, proc in reversed(self.processes):
            if proc.poll() is None:
                print(f"   -> Stopping {name} (PID: {proc.pid})...", end="")

                try:
                    if os.name == "posix":
                        # Graceful -> Terminate -> Kill (process group)
                        try:
                            os.killpg(proc.pid, signal.SIGINT)
                            proc.wait(timeout=5)
                            print("[green] Done (SIGINT).[/green]")
                            continue
                        except subprocess.TimeoutExpired:
                            pass

                        try:
                            os.killpg(proc.pid, signal.SIGTERM)
                            proc.wait(timeout=3)
                            print("[green] Done (SIGTERM).[/green]")
                            continue
                        except subprocess.TimeoutExpired:
                            pass

                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=2)
                        print("[yellow] Force-killed (SIGKILL).[/yellow]")

                    else:
                        # Windows: try CTRL_BREAK_EVENT for the process group
                        sent_break = False
                        try:
                            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                            sent_break = True
                            proc.wait(timeout=5)
                            print("[green] Done (CTRL_BREAK).[/green]")
                            continue
                        except Exception:
                            # Fall back if CTRL_BREAK not supported
                            pass

                        try:
                            proc.terminate()
                            proc.wait(timeout=3)
                            print("[green] Done (terminate).[/green]" if not sent_break else "")
                            continue
                        except subprocess.TimeoutExpired:
                            pass

                        proc.kill()
                        proc.wait(timeout=2)
                        print("[yellow] Force-killed.[/yellow]")

                except Exception as e:
                    print(f"[bold red] Error stopping {name}: {e}[/bold red]")

        self.processes = []
        print("\n✨ All services have been shut down. Goodbye!")

    def _stream_output(self, name, process, log_queue):
        """Reads a process's stdout and puts lines into the queue."""
        try:
            for line in iter(process.stdout.readline, ""):
                log_queue.put((name, line))
        except Exception:
            pass
        finally:
            try:
                process.stdout.close()
            except Exception:
                pass

    def _print_log_line(self):
        """Gets and prints a single log line from the queue if available."""
        port_regex = re.compile(r"http://localhost:(\d+)")
        try:
            name, line = self.log_queue.get_nowait()
            line = line.strip()
            if line:
                log_text = Text.from_ansi(line)
                print(Text.from_markup(f"[{self.services[name]['color']}][{name.upper():^10}][/] ") + log_text)

                match = port_regex.search(line)
                if match and name == "frontend" and not self._browser_opened:
                    port = match.group(1)
                    print(f"🌐 Opening http://localhost:{port} in your browser.")
                    try:
                        webbrowser.open_new_tab(f"http://localhost:{port}")
                        self._browser_opened = True
                    except webbrowser.Error:
                        print(f"[yellow]⚠️ Could not automatically open browser. Please navigate to http://localhost:{port} manually.[/yellow]")
                if "Failed to get tools from server: 'FastMCP'" in line:
                    print(f"[bold red]Fatal: {line} [/bold red]")
        except queue.Empty:
            pass

    def _flush_log_queue(self):
        """Prints all remaining logs in the queue."""
        while not self.log_queue.empty():
            self._print_log_line()


@app.callback()
def main(ctx: typer.Context):
    """
    Dingent Agent Framework CLI
    """
    cli_context = CliContext()

    if not cli_context.is_in_project:
        pass

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
    """Runs the Backend, and Frontend services concurrently."""
    cli_ctx: CliContext = ctx.obj
    env_info = EnvironmentInfo()
    runner = ServiceRunner(env_info, cli_ctx)
    runner.run()


@plugin_app.command("list")
def plugin_list(ctx: typer.Context):
    cli_ctx: CliContext = ctx.obj
    if not cli_ctx.is_in_project:
        logger.error("❌ Error: Not inside a dingent project. (Cannot find 'dingent.toml')")
        raise typer.Exit(code=1)
    if cli_ctx.plugin_manager:
        plugins = cli_ctx.plugin_manager.list_plugins()
        print("\nAll registered plugins:")
        for plugin in plugins.values():
            print(f" - {plugin.name} ({plugin.description})")
    else:
        logger.error("❌ Error: Plugin manager not initialized.")


@assistant_app.command("list")
def assistant_list(ctx: typer.Context):
    cli_ctx: CliContext = ctx.obj
    if not cli_ctx.is_in_project:
        logger.error("❌ Error: Not inside a dingent project. (Cannot find 'dingent.toml')")
        raise typer.Exit(code=1)
    if cli_ctx.assistant_manager:
        assistants = cli_ctx.assistant_manager.list_assistants()
        print("\nAll registered assistants:")
        for assistant in assistants.values():
            print(f" - {assistant.name} ({assistant.description})")
            print("     Tools:")
            for tool in assistant.tools:
                print(f"       - Name: {tool.name}, From Plugin: {tool.plugin_name}")
    else:
        logger.error("❌ Error: Assistant manager not initialized.")


@assistant_app.command("enable")
def assistant_enable(name, ctx: typer.Context):
    pass


@assistant_app.command("test")
def assistant_test(name: str, ctx: typer.Context):
    cli_ctx: CliContext = ctx.obj
    if not cli_ctx.is_in_project:
        logger.error("❌ Error: Not inside a dingent project. (Cannot find 'dingent.toml')")
        raise typer.Exit(code=1)
    if cli_ctx.assistant_manager:
        try:
            assistant = cli_ctx.assistant_manager.get_assistant(name)
            print(f"Successfully retrieved assistant: {assistant.name}")
        except Exception as e:
            print(f"[bold red]❌ Error: {e}[/bold red]")
    else:
        logger.error("❌ Error: Assistant manager not initialized.")


def run_services_programmatically():
    """
    Initializes and runs all services programmatically, mirroring the
    'dingent run' CLI command.

    This function can be imported and called from other Python scripts.
    """
    logger.info("Attempting to start Dingent services programmatically...")
    try:
        cli_ctx = CliContext()
        if not cli_ctx.is_in_project:
            logger.error("❌ Cannot start services: Not inside a Dingent project (dingent.toml not found).")
            raise FileNotFoundError("Not in a valid Dingent project directory.")

        env_info = EnvironmentInfo()

        runner = ServiceRunner(env_info, cli_ctx)
        runner.run()

    except Exception as e:
        logger.error(f"A critical error occurred while trying to run services: {e}")
        raise


if __name__ == "__main__":
    print("Starting the Dingent environment from an external script...")
    try:
        run_services_programmatically()
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting.")
    except Exception as e:
        print(f"\nFailed to start services: {e}")
