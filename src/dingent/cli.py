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

import click
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.main import cookiecutter

PROD_REPO_URL = "https://github.com/saya-ashen/Dingent.git"
DEV_REPO_URL = "/home/saya/Workspace/Dingent"

AVAILABLE_TEMPLATES = ["basic"]
IS_DEV_MODE = os.getenv("DINGENT_DEV")

REPO_URL = DEV_REPO_URL if IS_DEV_MODE else PROD_REPO_URL


def is_uv_installed():
    """Checks if 'uv' is available in the system's PATH."""
    return shutil.which("uv") is not None


def get_frontend_installer():
    """
    Determines the available frontend package manager.
    Prefers 'bun', falls back to 'npm'.
    Returns a tuple: (tool_name, install_command_list) or (None, None).
    """
    if shutil.which("bun"):
        return "bun", ["bun", "install"]
    if shutil.which("npm"):
        return "npm", ["npm", "install"]
    return None, None


@click.group()
def cli():
    """A CLI for the Dingent framework."""
    pass


@cli.command()
@click.argument("project_name")
@click.option(
    "--template",
    "-t",
    type=click.Choice(AVAILABLE_TEMPLATES, case_sensitive=False),
    default="basic",
    help="The project template to use.",
)
@click.option("--checkout", "-c", default=None, help="The branch, tag, or commit to checkout.")
def init(project_name, template, checkout):
    """Creates a new agent project by pulling a template from the git repo."""
    click.secho(f"🚀 Initializing project from git repository: {REPO_URL}", fg="green")

    template_dir_in_repo = f"templates/{template}"

    try:
        created_project_path = cookiecutter(
            REPO_URL,
            directory=template_dir_in_repo,
            checkout=checkout,
            no_input=False,
            extra_context={"project_slug": project_name},
            output_dir=".",
        )

        click.secho("\n✅ Project structure created successfully!", fg="green")

        click.secho("\n✨ Converting each .sql file to a separate .db database...", fg="cyan")

        project_path = Path(created_project_path)
        sql_dir = project_path / "mcp" / "data"

        if not sql_dir.is_dir():
            click.secho(f"⚠️  Warning: SQL data directory not found at '{sql_dir}'. Skipping database creation.", fg="yellow")
        else:
            sql_files = sorted(sql_dir.glob("*.sql"))

            if not sql_files:
                click.secho(f"ℹ️  Info: No .sql files found in '{sql_dir}'. Nothing to do.", fg="blue")
            else:
                click.echo(f"   -> Found {len(sql_files)} SQL file(s).")
                success_count = 0
                error_count = 0

                for sql_file in sql_files:
                    db_path = sql_file.with_suffix(".db")

                    try:
                        click.echo(f"      - Converting '{sql_file.name}'  ->  '{db_path.name}'")

                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()

                        with open(sql_file, encoding="utf-8") as f:
                            sql_script = f.read()

                        cursor.executescript(sql_script)
                        conn.commit()
                        conn.close()

                        success_count += 1

                    except sqlite3.Error as e:
                        click.secho(f"        ❌ Error: {e}", fg="red")
                        if db_path.exists():
                            db_path.unlink()
                        error_count += 1

                summary_color = "green" if error_count == 0 else "yellow"
                click.secho(f"\n✅ Conversion complete. {success_count} succeeded, {error_count} failed.", fg=summary_color)

        click.secho("\n📦 Installing project dependencies with 'uv sync'...", fg="cyan")

        if not is_uv_installed():
            click.secho("⚠️ Warning: 'uv' command not found. Skipping dependency installation.", fg="yellow")
            click.echo("Please install uv (https://github.com/astral-sh/uv) and run 'uv sync' in the 'mcp' and 'backend' directories manually.")
        else:
            dirs_to_install = ["mcp", "backend"]
            install_errors = False

            for subdir_name in dirs_to_install:
                target_dir = project_path / subdir_name
                if target_dir.is_dir() and (target_dir / "pyproject.toml").is_file():
                    click.echo(f"   -> Found 'pyproject.toml' in '{subdir_name}'. Running 'uv sync'...")

                    try:
                        result = subprocess.run(
                            ["uv", "sync"],
                            cwd=str(target_dir),
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                        if result.returncode == 0:
                            click.secho(f"     ✅ Successfully installed dependencies in '{subdir_name}'.", fg="green")
                        else:
                            install_errors = True
                            click.secho(f"     ❌ Error installing dependencies in '{subdir_name}'.", fg="red")
                            click.echo("     --- UV Error Output ---")
                            click.echo(result.stderr)
                            click.echo("     -----------------------")

                    except Exception as e:
                        install_errors = True
                        click.secho(f"     ❌ An unexpected error occurred while running uv in '{subdir_name}': {e}", fg="red")
                else:
                    click.secho(f"   -> Skipping '{subdir_name}', directory or 'pyproject.toml' not found.", fg="blue")

            if not install_errors:
                click.secho("\n✅ All dependencies installed successfully!", fg="green")
            else:
                click.secho("\n⚠️  Some dependencies failed to install. Please check the errors above.", fg="yellow")

        click.secho("\n🌐 Installing frontend dependencies...", fg="cyan")

        tool_name, install_command = get_frontend_installer()

        if not tool_name:
            click.secho("⚠️ Warning: Neither 'bun' nor 'npm' found. Skipping frontend dependency installation.", fg="yellow")
            click.echo("   Please install Bun or Node.js and run the install command in the 'frontend' directory manually.")
        else:
            frontend_dir_name = "frontend"
            frontend_dir = project_path / frontend_dir_name

            if frontend_dir.is_dir() and (frontend_dir / "package.json").is_file():
                click.echo(f"   -> Found 'package.json' in '{frontend_dir_name}'. Running '{' '.join(install_command)}'...")

                try:
                    result = subprocess.run(install_command, cwd=str(frontend_dir), capture_output=True, text=True, check=False)
                    if result.returncode == 0:
                        click.secho(f"     ✅ Successfully installed frontend dependencies using {tool_name}.", fg="green")
                    else:
                        click.secho(f"     ❌ Error installing frontend dependencies with {tool_name}.", fg="red")
                        click.echo("     --- Installer Error Output ---")
                        click.echo(result.stderr)
                        click.echo("     ----------------------------")

                except Exception as e:
                    click.secho(f"     ❌ An unexpected error occurred while running {tool_name}: {e}", fg="red")
            else:
                click.secho(f"   -> Skipping '{frontend_dir_name}', directory or 'package.json' not found.", fg="blue")
        final_project_name = project_path.name
        click.secho("\n✅ Project initialized successfully!", fg="green", bold=True)
        click.echo("\nNext steps:")
        click.echo(f"  1. Navigate to your new project: cd {final_project_name}")
        click.echo("  2. Dependencies for backend, mcp, and frontend have been installed.")
        click.echo("  3. Start building your amazing agent!")

    except RepositoryNotFound:
        click.secho(f"\n❌ Error: Repository not found at {REPO_URL}", fg="red", bold=True)
        click.echo("Please check the URL and your network connection.")
        sys.exit(1)
    except Exception as e:
        click.secho(f"\n❌ An error occurred: {e}", fg="red", bold=True)
        sys.exit(1)


def stream_output(name, process, log_queue):
    """
    Reads a process's stdout line by line and puts it into a thread-safe queue.
    This function is intended to be run in a separate thread for each process.
    """
    # The 'iter' function with two arguments will call process.stdout.readline until
    # it returns an empty string (which happens when the process terminates).
    for line in iter(process.stdout.readline, ""):
        log_queue.put((name, line))
    process.stdout.close()


@cli.command()
def run():
    """Runs the MCP, Backend, and Frontend services concurrently for development."""

    # 1. Define services, their commands, working directories, and log colors
    services = {
        "mcp": {"command": ["python", "main.py"], "cwd": "mcp", "color": "blue"},
        "backend": {"command": ["langgraph", "dev", "--no-browser"], "cwd": "backend", "color": "magenta"},
        "frontend": {"command": ["bun", "dev"], "cwd": "frontend", "color": "yellow"},
    }

    # --- NEW: Resolve virtual environment paths for Python services ---
    click.secho("🔎 Locating service executables...", fg="cyan")
    python_services = ["mcp", "backend"]
    for name in python_services:
        service = services[name]
        service_dir = Path(service["cwd"])

        if not service_dir.is_dir():
            click.secho(f"❌ Error: Directory '{service_dir}' for '{name}' service not found.", fg="red")
            click.echo("Please run this command from the root of a Dingent project.")
            sys.exit(1)

        venv_path = service_dir / ".venv"
        if not venv_path.is_dir():
            click.secho(f"❌ Error: Virtual environment for '{name}' not found at '{venv_path}'.", fg="red")
            click.echo(f"Please run 'uv sync' in the '{service_dir}' directory to create it.")
            sys.exit(1)

        # Determine the correct subdirectory for executables based on OS
        bin_dir = "Scripts" if sys.platform == "win32" else "bin"

        # Get the executable name and construct the full path
        executable_name = service["command"][0]
        executable_path = venv_path / bin_dir / executable_name

        # Add .exe suffix for Windows if it's not already there
        if sys.platform == "win32" and not executable_path.suffix:
            executable_path = executable_path.with_suffix(".exe")

        if not executable_path.is_file():
            click.secho(f"❌ Error: Executable '{executable_name}' not found for '{name}' at '{executable_path}'.", fg="red")
            click.echo("The virtual environment might be corrupted. Try recreating it.")
            sys.exit(1)

        # Update the command with the absolute path to the venv executable
        service["command"][0] = str(executable_path.absolute())
        click.echo(f"  -> Found '{name}' executable: {service['command'][0]}")
    # --- END NEW SECTION ---

    # Verify the frontend command is available
    frontend_cmd = services["frontend"]["command"][0]
    if not shutil.which(frontend_cmd):
        click.secho(f"❌ Error: Command '{frontend_cmd}' for 'frontend' service not found.", fg="red")
        click.echo("Please ensure Bun is installed and in your system's PATH.")
        sys.exit(1)

    processes = []
    threads = []
    log_queue = queue.Queue()

    click.secho("\n🚀 Starting all development services...", fg="cyan", bold=True)
    try:
        # 2. Start all processes and their corresponding log-streaming threads
        for name, service in services.items():
            proc = subprocess.Popen(service["command"], cwd=service["cwd"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", bufsize=1)
            processes.append((name, proc))

            thread = threading.Thread(target=stream_output, args=(name, proc, log_queue))
            thread.daemon = True
            thread.start()
            threads.append(thread)

            click.secho(f"✅ {name.capitalize()} service started (PID: {proc.pid}).", fg="green")

        # 3. Give services a moment to initialize, then open the browser
        click.echo("\nGiving services a moment to warm up...")
        time.sleep(3)
        click.secho("🌐 Opening http://localhost:3000 in your browser.", bold=True)
        webbrowser.open_new_tab("http://localhost:3000")

        click.secho("\n--- Real-time Logs (Press Ctrl+C to stop) ---", bold=True)

        # 4. Main loop to print logs from the queue and check process status
        active_processes = list(processes)
        while active_processes:
            # Check for terminated processes
            for i in range(len(active_processes) - 1, -1, -1):
                name, proc = active_processes[i]
                if proc.poll() is not None:
                    # ---- START MODIFICATION ----
                    # Process has terminated. Before exiting, drain the log queue
                    # to ensure we capture its final output (the error message).
                    click.secho(f"\n⏳ Service '{name}' terminated with code {proc.returncode}. Flushing logs...", fg="yellow")
                    time.sleep(0.5)  # Give the logger thread a moment to finish

                    while not log_queue.empty():
                        try:
                            log_name, line = log_queue.get_nowait()
                            prefix = click.style(f"[{log_name.upper():^8}]", fg=services[log_name]["color"])
                            click.echo(f"{prefix} {line.strip()}")
                        except queue.Empty:
                            break  # Should not happen, but for safety

                    click.secho(f"\n❌ Service '{name}' has terminated unexpectedly.", fg="red", bold=True)
                    raise RuntimeError(f"Service '{name}' exited.")
                    # ---- END MODIFICATION ----

            # Print logs from the queue
            try:
                name, line = log_queue.get_nowait()
                prefix = click.style(f"[{name.upper():^8}]", fg=services[name]["color"])
                click.echo(f"{prefix} {line.strip()}")
            except queue.Empty:
                time.sleep(0.1)

    except (KeyboardInterrupt, RuntimeError) as e:
        if isinstance(e, RuntimeError):
            click.secho(f"\nReason: {e}", fg="red")
        click.secho("\n\n🛑 Shutting down all services...", fg="yellow", bold=True)
    finally:
        # 5. Terminate all child processes on exit
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                # Give it a moment to terminate gracefully
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # If it doesn't terminate, force kill it
                    proc.kill()
                    proc.wait()
                click.secho(f"🔌 {name.capitalize()} service stopped.", fg="blue")
        click.secho("\n✨ All services have been shut down. Goodbye!", fg="green")
