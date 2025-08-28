"""
Dingent CLI (Simplified version for concurrent Frontend + Backend execution)

Commands:
  dingent run        Concurrently start backend (langgraph dev no UI) + frontend (node)
  dingent dev        Start langgraph dev with UI (backend only, for debugging Graph + API)
  dingent init       Create a new Agent project from a template
  dingent version    Show version

Optional Environment Variables:
  DINGENT_GRAPH_SPEC   Override default Graph entrypoint (default: dingent.engine.graph:make_graph)
  DINGENT_API_SPEC     Override default FastAPI application entrypoint (default: dingent.server.main:app)
"""

from __future__ import annotations

import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
from typing import Annotated

import psutil
import typer
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.main import cookiecutter
from rich import print
from rich.text import Text

from .context import CliContext

app = typer.Typer(help="Dingent Agent Framework CLI")

DEFAULT_GRAPH_SPEC = "dingent.engine.graph:make_graph"
DEFAULT_API_SPEC = "dingent.server.app_factory:app"
ENV_GRAPH_SPEC = "DINGENT_GRAPH_SPEC"
ENV_API_SPEC = "DINGENT_API_SPEC"

PROD_REPO_URL = "https://github.com/saya-ashen/Dingent.git"
# When running in development mode, this can point to a local repository for easier debugging
DEV_REPO_URL = "/home/saya/Workspace/Dingent"

AVAILABLE_TEMPLATES = ["basic"]
IS_DEV_MODE = os.getenv("DINGENT_DEV")

REPO_URL = DEV_REPO_URL if IS_DEV_MODE else PROD_REPO_URL

DEFAULT_DINGENT_TOML = """
[project]
[backend]
port = 8000
plugins.directory = "plugins"

[dashboard]
port = 8501

[frontend]
port = 3000
"""

# --------- Utility Functions ---------


def _ensure_project_root(cli_ctx: CliContext) -> CliContext:
    """
    Checks if the current directory is a Dingent project. If not, prompts the user to create dingent.toml.
    """
    if not cli_ctx.project_root:
        print("[bold yellow]⚠️ Not a Dingent project directory (missing dingent.toml).[/bold yellow]")
        create_file = typer.confirm("Would you like to create a default dingent.toml configuration file here?")
        if create_file:
            cwd = Path.cwd()
            project_name = cwd.name
            config_path = cwd / "dingent.toml"
            config_content = DEFAULT_DINGENT_TOML.format(project_name=project_name)
            config_path.write_text(config_content, encoding="utf-8")
            print(f"[bold green]✅ Default config created at {config_path}. Please re-run the command to start.[/bold green]")
            raise typer.Exit()
        else:
            print("[bold red]Operation cancelled.[/bold red]")
            raise typer.Exit()
    return cli_ctx


def _resolve_node_binary() -> str:
    """
    Gets the node executable path using nodejs_wheel.
    """
    try:
        from nodejs_wheel import node

        cp = node(
            args=["-e", "console.log(process.execPath)"],
            return_completed_process=True,
            capture_output=True,
            text=True,
        )
        if isinstance(cp, subprocess.CompletedProcess) and cp.returncode == 0 and cp.stdout:
            return cp.stdout.strip()
        raise RuntimeError("nodejs_wheel returned an exception")
    except Exception as e:
        raise RuntimeError(f"Could not resolve Node executable: {e}")


def _create_backend_config(cli_ctx: CliContext) -> Path:
    """
    Generates a configuration file for the backend's langgraph.dev inside the project's .dingent directory.
    Returns the path to the config file.
    """
    graph_spec = os.getenv(ENV_GRAPH_SPEC, DEFAULT_GRAPH_SPEC)
    api_spec = os.getenv(ENV_API_SPEC, DEFAULT_API_SPEC)

    # Create the .dingent directory if it doesn't exist
    dingent_dir = cli_ctx.project_root / ".dingent"
    dingent_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = dingent_dir / "langgraph.json"
    cfg = {
        "graphs": {"agent": graph_spec},
        "http": {"app": api_spec},
        "dependencies": ["langchain_openai"],
        "metadata": {"provider": "dingent", "mode": "run"},
    }
    cfg_path.write_text(
        import_json_dumps(cfg),
        encoding="utf-8",
    )
    return cfg_path


def import_json_dumps(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, indent=2)


_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []  # Prevent cleanup by garbage collector


class ProjectInitializer:
    """Handles the logic for the 'init' command."""

    def __init__(self, project_name, template, checkout):
        self.project_name = project_name
        self.template = template
        self.checkout = checkout
        self.project_path = None

    def run(self):
        """Executes the entire project initialization workflow."""
        try:
            self._create_from_template()
            self._print_final_summary()
        except RepositoryNotFound:
            print(f"[bold red]\n❌ Error: Repository not found at {REPO_URL}[/bold red]")
            print("[bold red]\nPlease check the URL and your network connection.[/bold red]")
            raise typer.Exit()
        except Exception as e:
            print(f"[bold red]\nAn unexpected error occurred: {e}[/bold red]")
            raise typer.Exit()

    def _create_from_template(self):
        """Builds the project using Cookiecutter."""
        print(f"[bold green]🚀 Initializing project from Git repository: {REPO_URL}[/bold green]")
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

    def _print_final_summary(self):
        """Prints the final success message and next steps."""
        final_project_name = self.project_path.name
        print("[bold green]\n🎉 Project initialized successfully![/bold green]")
        print("\nNext steps:")
        print(f"  1. Change into the project directory: cd {final_project_name}")
        print("  2. Start all services: dingent run")


class Service:
    def __init__(
        self,
        name: str,
        command: list[str],
        cwd: Path,
        color: str,
        env: dict[str, str] | None = None,
        open_browser_hint: bool = False,
    ):
        self.name = name
        self.command = command
        self.cwd = cwd
        self.color = color
        self.env = env or {}
        self.open_browser_hint = open_browser_hint
        self.process: subprocess.Popen | None = None


class ServiceSupervisor:
    def __init__(self, services: list[Service], auto_open_frontend: bool = True):
        self.services = services
        self.auto_open_frontend = auto_open_frontend
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._browser_opened = False
        self._stop_event = threading.Event()

    def start_all(self):
        print("[bold cyan]🚀 Starting services...[/bold cyan]")
        for svc in self.services:
            self._start_service(svc)

        t = threading.Thread(target=self._log_loop, daemon=True)
        t.start()

        print("[bold green]✓ All services started. Real-time logs below (Ctrl+C to exit).[/bold green]")
        try:
            while not self._stop_event.is_set():
                for svc in self.services:
                    if svc.process and svc.process.poll() is not None:
                        print(f"\n[bold red]Service {svc.name} has exited with code {svc.process.returncode}. Shutting down other services...[/bold red]")
                        self.stop_all()
                        raise typer.Exit(1)
                time.sleep(0.3)
        except KeyboardInterrupt:
            if not hasattr(self, "_shutting_down"):
                self._shutting_down = True
                print("\n[bold yellow]Received interrupt signal. Shutting down services (press Ctrl+C again to force quit)...[/bold yellow]")
                try:
                    self.stop_all()
                except KeyboardInterrupt:
                    print("\n[bold red]Second interrupt: Forcibly terminating all processes now.[/bold red]")
                    self.stop_all(force=True)
            else:
                print("\n[bold red]Received interrupt again, force quitting...[/bold red]")
                self.stop_all(force=True)

    def stop_all(self, force: bool = False):
        self._stop_event.set()
        for svc in reversed(self.services):
            if svc.process and svc.process.poll() is None:
                _terminate_process_tree(svc.process, svc.name, force=force)
        print("[bold blue]🛑 All processes have been terminated.[/bold blue]")

        global _TEMP_DIRS
        for td in _TEMP_DIRS:
            try:
                td.cleanup()
            except Exception:
                pass
        _TEMP_DIRS.clear()

    def _start_service(self, svc: Service):
        env = {**os.environ, **svc.env}
        popen_kwargs = {
            "cwd": str(svc.cwd),
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "env": env,
            "text": True,
            "bufsize": 1,
            "errors": "replace",
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        else:
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            svc.process = subprocess.Popen(svc.command, **popen_kwargs)
        except FileNotFoundError:
            print(f"[bold red]❌ Failed to start {svc.name}: Command not found: {svc.command[0]}[/bold red]")
            raise typer.Exit(1)
        threading.Thread(target=self._stream_reader, args=(svc,), daemon=True).start()
        print(f"[bold green]✓ {svc.name} (PID {svc.process.pid}) started: {' '.join(svc.command)}[/bold green]")

    def _stream_reader(self, svc: Service):
        assert svc.process and svc.process.stdout
        for line in iter(svc.process.stdout.readline, ""):
            if not line:
                break
            self.log_queue.put((svc.name, line.rstrip("\n")))
        try:
            svc.process.stdout.close()
        except Exception:
            pass

    def _log_loop(self):
        port_regex = re.compile(r"http://localhost:(\d+)")
        while not self._stop_event.is_set():
            try:
                name, line = self.log_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            svc = next((s for s in self.services if s.name == name), None)
            color = svc.color if svc else "white"
            text = Text.from_markup(f"[{color}][{name.upper():^8}][/]: {line}")
            print(text)

            if svc and svc.open_browser_hint and self.auto_open_frontend and not self._browser_opened:
                m = port_regex.search(line)
                if m:
                    url = f"http://localhost:{m.group(1)}"
                    print(f"[bold blue]🌐 Opening browser: {url}[/bold blue]")
                    try:
                        webbrowser.open_new_tab(url)
                        self._browser_opened = True
                    except Exception:
                        print("[yellow]⚠️ Could not open browser automatically.[/yellow]")


def _terminate_process_tree(proc: subprocess.Popen, name: str, force: bool = False):
    """
    Recursively terminates a process and all its descendants using psutil.
    """
    if proc.poll() is not None:
        return

    print(f"[yellow]Stopping {name} (PID {proc.pid}) ...[/yellow]", end="")

    try:
        main_proc = psutil.Process(proc.pid)
        children = main_proc.children(recursive=True)

        if not force:
            main_proc.terminate()
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass

            _, alive = psutil.wait_procs([main_proc] + children, timeout=8)
            if not alive:
                print("[green] ✓[/green]")
                return

        main_proc.kill()
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass

        psutil.wait_procs([main_proc] + children, timeout=5)
        print("[yellow] (force/kill) ✓[/yellow]")

    except psutil.NoSuchProcess:
        print("[green] ✓ (already terminated)[/green]")
    except Exception as e:
        print(f"[red] Failed: {e}[/red]")


@app.command()
def run(
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open the frontend page in a browser automatically."),
):
    """
    Concurrently starts the backend and frontend services.
    """
    cli_ctx = CliContext()
    cli_ctx = _ensure_project_root(cli_ctx)

    try:
        node_bin = _resolve_node_binary()
    except Exception as e:
        print(f"[bold red]❌ Failed to resolve Node: {e}[/bold red]")
        raise typer.Exit(1)

    backend_cmd = [
        "uvicorn",
        "dingent.server.copilot_server:app",
        "--host",
        "localhost",
        "--port",
        str(cli_ctx.backend_port),
    ]
    frontend_cmd = [node_bin, "server.js", "--port", str(cli_ctx.frontend_port)]

    services = [
        Service(
            name="backend",
            command=backend_cmd,
            cwd=cli_ctx.project_root,
            color="magenta",
        ),
        Service(
            name="frontend",
            command=frontend_cmd,
            cwd=cli_ctx.frontend_path,
            color="cyan",
            env={"DING_BACKEND_URL": f"http://localhost:{cli_ctx.backend_port}"},
            open_browser_hint=True,
        ),
    ]

    supervisor = ServiceSupervisor(services, auto_open_frontend=not no_browser)
    supervisor.start_all()


@app.command()
def dev(
    open_ui: bool = typer.Option(True, "--ui/--no-ui", help="Start the official langgraph dev UI"),
    with_frontend: bool = typer.Option(True, "--with-frontend", help="Also start the frontend"),
    no_browser: bool = typer.Option(False, "--no-browser", help="When --with-frontend is enabled, do not open the browser automatically"),
):
    """
    Starts the development server, primarily for debugging the backend Graph and API.
    """
    if not open_ui and not with_frontend:
        print("[yellow]No action specified (use --ui or --with-frontend). Exiting.[/yellow]")
        raise typer.Exit(0)

    cli_ctx = CliContext()
    cli_ctx = _ensure_project_root(cli_ctx)

    if open_ui and not with_frontend:
        try:
            from .dev_runner import start_langgraph_ui
        except Exception as e:
            print(f"[bold red]Failed to import dev_runner: {e}[/bold red]")
            raise typer.Exit(1)
        start_langgraph_ui()
        return

    # MODIFICATION: Using the new function to create the config
    cfg_path = _create_backend_config(cli_ctx)
    backend_cmd = [
        "langgraph",
        "dev",
        "--allow-blocking",
        "--no-reload",
        "--port",
        str(cli_ctx.backend_port),
        "--config",
        str(cfg_path),
    ]

    services = [
        Service(
            name="backend-ui" if open_ui else "backend",
            command=backend_cmd,
            cwd=cli_ctx.project_root,
            env={"DINGENT_DEV": "true"},
            color="magenta",
            open_browser_hint=True,
        ),
    ]

    if with_frontend:
        try:
            node_bin = _resolve_node_binary()
        except Exception as e:
            print(f"[bold red]❌ Failed to resolve Node: {e}[/bold red]")
            raise typer.Exit(1)

        frontend_cmd = [node_bin, "server.js", "--port", str(cli_ctx.frontend_port)]
        services.append(
            Service(
                name="frontend",
                command=frontend_cmd,
                cwd=cli_ctx.frontend_path,
                color="cyan",
                env={
                    "DING_BACKEND_URL": f"http://localhost:{cli_ctx.backend_port}",
                    "DINGENT_DEV": "true",
                },
            )
        )

    supervisor = ServiceSupervisor(services, auto_open_frontend=not no_browser)
    supervisor.start_all()


@app.command("init")
def init(
    project_name: Annotated[str, typer.Argument(help="The name of the new project")],
    template: Annotated[str, typer.Option(help="The template to use for creating the project")] = "basic",
    checkout: Annotated[str, typer.Option(help="The branch, tag, or commit to check out")] = "main",
):
    """Create a new Agent project from a template."""
    initializer = ProjectInitializer(project_name, template, checkout)
    initializer.run()


@app.command()
def version():
    """Show the Dingent version"""
    try:
        from importlib.metadata import version as _v

        ver = _v("dingent")
    except Exception:
        ver = "unknown"
    print(f"Dingent version: {ver}")


def main():
    app()


if __name__ == "__main__":
    main()
