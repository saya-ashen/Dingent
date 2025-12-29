"""
Dingent CLI (Simplified version for concurrent Frontend + Backend execution)

Commands:
  dingent run        Concurrently start backend (langgraph dev no UI) + frontend (node)
  dingent version    Show version
"""

from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import shutil
import webbrowser
from pathlib import Path
from typing import Annotated

import psutil
import typer
from cookiecutter.exceptions import RepositoryNotFound
from cookiecutter.main import cookiecutter
from rich import print
from rich.text import Text
import hashlib

from dingent.cli.context import CliContext

app = typer.Typer(help="Dingent Agent Framework CLI")


PROD_REPO_URL = "https://github.com/saya-ashen/Dingent.git"
# When running in development mode, this can point to a local repository for easier debugging
DEV_REPO_URL = "/home/saya/Workspace/Dingent"

IS_DEV_MODE = os.getenv("DINGENT_DEV")

REPO_URL = DEV_REPO_URL if IS_DEV_MODE else PROD_REPO_URL

DEFAULT_DINGENT_TOML = """
backend_port = 8000
frontend_port = 3000
"""

# --------- Utility Functions ---------


def _prepare_static_assets(cli_ctx: CliContext) -> Path:
    """
    根据运行模式准备静态资源路径。
    自动检测版本变更，如果有更新则重新解压。
    """
    bundle_dir = Path(sys._MEIPASS)
    tar_source = bundle_dir / "static.tar.gz"

    # 设定解压目标
    temp_dir = Path(tempfile.gettempdir()) / "dingent_runtime" / "static"
    version_file = temp_dir.parent / "static_version.txt"  # 用于记录指纹

    # 1. 计算内置包的指纹 (MD5)
    # 读取 tar.gz 的前 8KB 甚至整个文件做 hash 都可以，这里读整个文件确保准确
    try:
        with open(tar_source, "rb") as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
    except Exception:
        current_hash = "unknown"

    # 2. 检查是否需要更新
    need_update = True
    if temp_dir.exists() and version_file.exists():
        try:
            cached_hash = version_file.read_text().strip()
            if cached_hash == current_hash:
                need_update = False
        except Exception:
            pass

    # 3. 如果需要更新，先清理旧文件，再解压
    if need_update:
        print(f"[bold blue]📦 Detected update (Hash: {current_hash[:8]}). Extracting assets...[/bold blue]")

        # 移除旧目录（如果存在）
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                print(f"[bold yellow]⚠️ Warning: Could not clean old assets (Locked?): {e}[/bold yellow]")
                # 如果删除失败（例如文件被占用），尝试直接覆盖，或者报错

        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with tarfile.open(tar_source, "r:gz") as tar:
                tar.extractall(path=temp_dir, filter="data")

            # 解压成功后，写入版本文件
            version_file.write_text(current_hash)

        except Exception as e:
            print(f"[bold red]❌ Failed to extract assets: {e}[/bold red]")
            raise typer.Exit(1)
    # else:
    # print("✅ Assets are up to date.")

    return temp_dir


def _ensure_project_root(explicit_dir: Path | None = None) -> bool:
    """
    Ensure the application is running in the correct data directory.
    For a service/software, we use the OS standard AppData folder.
    """
    APP_NAME = "dingent"
    if explicit_dir:
        # 如果用户指定了目录，将其转换为绝对路径
        app_dir = explicit_dir.resolve()
        print(f"[bold blue]📂 Using custom data directory: {app_dir}[/bold blue]")
    else:
        # 否则使用系统标准目录
        app_dir = Path(typer.get_app_dir(APP_NAME))
        # 只有在默认模式下才打印这个，避免 verbose
        # print(f"[bold blue]📂 Using system data directory: {app_dir}[/bold blue]")

    # 2. 确保目录存在
    if not app_dir.exists():
        try:
            app_dir.mkdir(parents=True, exist_ok=True)
            print(f"[bold blue]📂 Created application data directory: {app_dir}[/bold blue]")
        except Exception as e:
            print(f"[bold red]❌ Failed to create app directory {app_dir}: {e}[/bold red]")
            raise typer.Exit(1)

    # 3. [关键步骤] 强制将当前工作目录 (CWD) 切换到这个数据目录
    # 这样后续所有的 CliContext 读取、日志生成、临时文件都会在这个安全目录下进行
    os.chdir(app_dir)

    # 4. 检查并创建配置文件
    config_path = app_dir / "dingent.toml"

    if config_path.exists():
        # 如果文件已存在，直接返回，不需要重新加载
        return False

    # --- 文件不存在，创建默认配置 ---
    print(f"[bold blue]ℹ️ Initializing configuration in {config_path}...[/bold blue]")
    try:
        # 服务软件通常不需要动态的项目名，直接叫 dingent-service 即可
        config_content = DEFAULT_DINGENT_TOML.format(project_name="dingent-service")
        config_path.write_text(config_content, encoding="utf-8")
        print("[bold green]✅ Configuration created.[/bold green]")
        return True
    except Exception as e:
        print(f"[bold red]❌ Failed to write config file: {e}[/bold red]")
        raise typer.Exit(1)


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
        cwd: Path | None,
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
        except FileNotFoundError as e:
            print(f"[bold red]❌ Failed to start service {svc.name}: {e}[/bold red]")
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
    data_dir: Annotated[Path | None, typer.Option("--data-dir", "-d", help="Specify a custom data directory for config and logs.")] = None,
):
    """
    Concurrently starts the backend and frontend services.
    """
    cli_ctx = CliContext()
    was_created = _ensure_project_root(data_dir)
    if was_created:
        cli_ctx = CliContext()

    try:
        node_bin = _resolve_node_binary()
    except Exception as e:
        print(f"[bold red]❌ Failed to resolve Node: {e}[/bold red]")
        raise typer.Exit(1)

    if getattr(sys, "frozen", False):
        backend_cmd = [
            sys.executable,
            "internal-backend",
            "localhost",
            str(cli_ctx.backend_port),
        ]
    else:
        backend_cmd = [
            "uvicorn",
            "dingent.server.main:app",
            "--host",
            "localhost",
            "--port",
            str(cli_ctx.backend_port),
        ]
    static_path = _prepare_static_assets(cli_ctx)
    services = [
        Service(
            name="backend",
            command=backend_cmd,
            cwd=cli_ctx.project_root,
            color="magenta",
        ),
        Service(
            name="frontend",
            command=[node_bin, "frontend/server.js"],
            cwd=static_path,
            color="cyan",
            env={
                "DING_BACKEND_URL": f"http://localhost:{cli_ctx.backend_port}",
                "PORT": str(cli_ctx.frontend_port or 3000),
            },
            open_browser_hint=True,
        ),
    ]

    supervisor = ServiceSupervisor(services, auto_open_frontend=not no_browser)
    supervisor.start_all()


@app.command(hidden=True)
def internal_backend(host: str, port: int, app_str: str = "dingent.server.main:app"):
    """
    (Internal) 仅供打包后的 EXE 内部调用，用于启动 Uvicorn
    """
    import uvicorn

    # 动态导入 app 对象，或者直接传字符串（uvicorn 只是在 EXE 内调用 python 模块）
    uvicorn.run(app_str, host=host, port=port)


@app.command()
def version():
    """Show the Dingent version"""
    try:
        from importlib.metadata import version as _v

        ver = _v("dingent")
    except Exception:
        ver = "unknown"
    print(f"Dingent version: {ver}")


@app.callback(invoke_without_command=True)
def main_entry(ctx: typer.Context):
    """
    Dingent Agent Framework CLI
    If no command is provided, acts as 'dingent run'.
    """
    # 如果用户没有输入任何子命令 (如 run, dev, version)
    if ctx.invoked_subcommand is None:
        # 手动调用 run 函数，传入默认参数
        run(no_browser=False)


def main():
    app()


if __name__ == "__main__":
    main()
