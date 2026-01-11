"""
Dingent CLI (Simplified version for concurrent Frontend + Backend execution)

Commands:
  dingent run        Concurrently start backend (langgraph dev no UI) + frontend (node)
  dingent version    Show version
"""

from __future__ import annotations

import atexit
import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Annotated

import psutil
import typer
from rich import print
from rich.text import Text

app = typer.Typer(help="Dingent Agent Framework CLI")


IS_DEV_MODE = os.getenv("DINGENT_DEV")


# --------- Utility Functions ---------


_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []  # Prevent cleanup by garbage collector


class Service:
    def __init__(
        self,
        name: str,
        command: list[str],
        cwd: Path | None,
        color: str,
        env: dict[str, str] | None = None,
        open_browser_hint: bool = False,
        health_check_url: str | None = None,
        depends_on: list[str] | None = None,
    ):
        self.name = name
        self.command = command
        self.cwd = cwd
        self.color = color
        self.env = env or {}
        self.open_browser_hint = open_browser_hint
        self.process: subprocess.Popen | None = None
        self.is_ready = threading.Event()
        self.health_check_url = health_check_url
        self.depends_on = depends_on or []


def _wait_for_health(url: str, timeout: float = 60, interval: float = 0.5) -> bool:
    """等待服务健康检查通过"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass
        time.sleep(interval)
    return False


class ServiceSupervisor:
    def __init__(self, services: list[Service], auto_open_frontend: bool = True):
        self.services = services
        self.auto_open_frontend = auto_open_frontend
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._browser_opened = False
        self._stop_event = threading.Event()
        self._shutting_down = False

        atexit.register(self._cleanup_on_exit)

    def _setup_signal_handlers(self):
        """设置信号处理器"""

        def signal_handler(signum, frame):
            if not self._shutting_down:
                self._shutting_down = True
                print("\n[bold yellow]Received signal.  Shutting down.. .[/bold yellow]")
                self.stop_all()
                sys.exit(0)
            if signum and frame:
                pass

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        if os.name == "posix":
            signal.signal(signal.SIGHUP, signal_handler)

    def start_all(self):
        print("[bold cyan]🚀 Starting services...[/bold cyan]")

        started_services: dict[str, Service] = {}
        self._setup_signal_handlers()

        for svc in self.services:
            # 等待依赖服务就绪
            for dep_name in svc.depends_on:
                dep_svc = started_services.get(dep_name)
                if dep_svc:
                    print(f"[cyan]⏳ Waiting for {dep_name} to be ready...[/cyan]")
                    if not dep_svc.is_ready.wait(timeout=60):
                        print(f"[bold red]❌ Timeout waiting for {dep_name}[/bold red]")
                        self.stop_all()
                        raise typer.Exit(1)

            self._start_service(svc)
            started_services[svc.name] = svc

            # 如果有健康检查，启动后台线程等待
            if svc.health_check_url:
                threading.Thread(target=self._health_check_worker, args=(svc,), daemon=True).start()
            else:
                # 没有健康检查的服务直接标记为就绪
                svc.is_ready.set()

        t = threading.Thread(target=self._log_loop, daemon=True)
        t.start()

        print("[bold green]✓ All services started.[/bold green]")

        try:
            while not self._stop_event.is_set():
                for svc in self.services:
                    if svc.process and svc.process.poll() is not None:
                        print(f"\n[bold red]Service {svc.name} exited.[/bold red]")
                        self.stop_all()
                        raise typer.Exit(1)
                time.sleep(0.3)
        except KeyboardInterrupt:
            pass  # 由信号处理器处理

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

    def _cleanup_on_exit(self):
        """确保退出时清理所有子进程"""
        if not self._shutting_down:
            self._shutting_down = True
            self.stop_all(force=True)

    def _health_check_worker(self, svc: Service):
        """后台健康检查"""
        if _wait_for_health(svc.health_check_url or "", timeout=60):
            print(f"[bold green]✓ {svc.name} is ready![/bold green]")
            svc.is_ready.set()
        else:
            print(f"[bold red]❌ {svc.name} health check failed[/bold red]")


def _terminate_process_tree(proc: subprocess.Popen, name: str, force: bool = False):
    """改进的进程终止函数"""
    if proc.poll() is not None:
        return

    print(f"[yellow]Stopping {name} (PID {proc.pid}) .. .[/yellow]", end="")

    try:
        main_proc = psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        print("[green] ✓ (already gone)[/green]")
        return

    # 先收集所有子进程
    try:
        children = main_proc.children(recursive=True)
    except psutil.NoSuchProcess:
        children = []

    procs_to_kill = children + [main_proc]  # 先杀子进程，再杀父进程

    if not force:
        # 优雅终止
        for p in procs_to_kill:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass

        _, alive = psutil.wait_procs(procs_to_kill, timeout=5)

        if alive:
            # 强制终止存活的进程
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(alive, timeout=3)
    else:
        # 直接强制终止
        for p in procs_to_kill:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(procs_to_kill, timeout=3)

    print("[green] ✓[/green]")


@app.command()
def run(
    host: str = "localhost",
    port: int = 8000,
    ui_port: int = 3000,
    no_browser: bool = False,
    data_dir: Annotated[Path | None, typer.Option("--data-dir", "-d")] = None,
    dev: bool = False,
):
    """
    Concurrently starts the backend and frontend services.
    """
    # 1. 注入环境变量 (必须在导入 paths/settings 之前)
    if data_dir:
        os.environ["DINGENT_HOME"] = str(data_dir.resolve())

    # 2. 现在安全导入
    from dingent.cli.assets import asset_manager
    from dingent.core.paths import paths

    print("[cyan]🔍 Checking runtime environment...[/cyan]")

    # 3. 准备资源
    asset_paths = asset_manager.ensure_assets()
    node_bin = asset_paths["node_bin"]
    frontend_dir = asset_paths["frontend_dir"]
    frontend_script = asset_paths["frontend_script"]

    # 4. 构建启动命令
    if paths.is_frozen:
        # 生产环境：使用 sys.executable 调用 internal-backend
        backend_cmd = [
            sys.executable,
            "internal-backend",
            host,
            str(port),
        ]
        # 生产环境 Backend 不需要特定的 CWD，或者指向 bundle_dir 即可
        backend_cwd = paths.bundle_dir
    else:
        # 开发环境
        backend_cmd = [
            "uvicorn",
            "dingent.server.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--reload",
        ]
        # 开发环境 CWD 必须是项目根目录
        backend_cwd = paths.bundle_dir

    services = [
        Service(
            name="backend",
            command=backend_cmd,
            cwd=backend_cwd,
            color="magenta",
            env={**os.environ},
            health_check_url=f"http://{host}:{port}/api/v1/health",
        ),
    ]

    # 5. 前端服务
    if not dev:
        services.append(
            Service(
                name="frontend",
                command=[node_bin, frontend_script],
                cwd=frontend_dir,
                color="cyan",
                env={
                    "DING_BACKEND_URL": f"http://{host}:{port}",
                    "PORT": str(ui_port),
                    "HOSTNAME": host,
                },
                open_browser_hint=True,
                depends_on=["backend"],
            )
        )

    should_open_browser = (not no_browser) and (not dev)

    supervisor = ServiceSupervisor(services, auto_open_frontend=should_open_browser)
    supervisor.start_all()


@app.command(hidden=True)
def internal_backend(host: str, port: int):
    """
    (Internal) 仅供打包后的 EXE 内部调用，用于启动 Uvicorn
    """
    import uvicorn

    uvicorn.run("dingent.server.main:app", host=host, port=port)


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
