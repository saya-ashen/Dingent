"""
Dingent CLI (使用 asyncio.subprocess 重写)

Commands:
  dingent run        Concurrently start backend + frontend
  dingent version    Show version
"""

from __future__ import annotations

import asyncio
import os
import re
import signal
import sys
import tempfile
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(help="Dingent Agent Framework CLI")
console = Console()

IS_DEV_MODE = os.getenv("DINGENT_DEV")
_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []


# --------- Service Definition ---------


@dataclass
class ServiceConfig:
    name: str
    command: list[str]
    color: str
    cwd: Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    health_check_url: str | None = None
    depends_on: list[str] = field(default_factory=list)
    open_browser_hint: bool = False


# --------- Async Service Manager ---------


class AsyncServiceManager:
    def __init__(self, auto_open_browser: bool = True):
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.ready_events: dict[str, asyncio.Event] = {}
        self.auto_open_browser = auto_open_browser
        self._browser_opened = False
        self._shutdown_event = asyncio.Event()
        self._print_lock = asyncio.Lock()

    async def _safe_print(self, message: str):
        """线程安全的打印"""
        async with self._print_lock:
            console.print(message)

    async def _health_check(self, url: str, timeout: float = 60) -> bool:
        """异步健康检查"""
        import aiohttp

        start = asyncio.get_event_loop().time()
        async with aiohttp.ClientSession() as session:
            while asyncio.get_event_loop().time() - start < timeout:
                if self._shutdown_event.is_set():
                    return False
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        if resp.status == 200:
                            return True
                except Exception:
                    pass
                await asyncio.sleep(0.5)
        return False

    async def _wait_for_dependencies(self, service: ServiceConfig):
        """等待依赖服务就绪"""
        for dep_name in service.depends_on:
            if dep_name in self.ready_events:
                await self._safe_print(f"[cyan]⏳ {service.name} waiting for {dep_name}.. .[/cyan]")
                try:
                    await asyncio.wait_for(self.ready_events[dep_name].wait(), timeout=120)
                    await self._safe_print(f"[green]✓ {dep_name} is ready, starting {service.name}[/green]")
                except asyncio.TimeoutError:
                    await self._safe_print(f"[bold red]❌ Timeout waiting for {dep_name}[/bold red]")
                    raise

    async def _run_service(self, service: ServiceConfig):
        """运行单个服务"""
        # 初始化就绪事件
        self.ready_events[service.name] = asyncio.Event()

        # 等待依赖
        await self._wait_for_dependencies(service)

        # 准备环境变量
        merged_env = {**os.environ, **service.env}

        # 启动进程
        proc = await asyncio.create_subprocess_exec(
            *service.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=merged_env,
            cwd=str(service.cwd) if service.cwd else None,
        )
        self.processes[service.name] = proc
        await self._safe_print(f"[bold green]✓ {service.name} (PID {proc.pid}) started:  {' '.join(service.command)}[/bold green]")

        # 启动健康检查（如果有）
        health_task = None
        if service.health_check_url:
            health_task = asyncio.create_task(self._monitor_health(service))
        else:
            # 无健康检查，直接标记就绪
            self.ready_events[service.name].set()

        # 流式读取输出
        await self._stream_output(service, proc)

        # 清理健康检查任务
        if health_task and not health_task.done():
            health_task.cancel()

        # 进程退出处理
        await proc.wait()
        if not self._shutdown_event.is_set():
            await self._safe_print(f"[bold red]✗ {service.name} exited unexpectedly (code {proc.returncode})[/bold red]")
            # ���发全局关闭
            self._shutdown_event.set()

    async def _stream_output(self, service: ServiceConfig, proc: asyncio.subprocess.Process):
        """流式输出日志"""
        port_regex = re.compile(r"http://localhost:(\d+)")

        assert proc.stdout is not None
        while not self._shutdown_event.is_set():
            try:
                line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=0.5)
            except asyncio.TimeoutError:
                if proc.returncode is not None:
                    break
                continue

            if not line_bytes:
                break

            line = line_bytes.decode(errors="replace").rstrip()
            await self._safe_print(f"[{service.color}][{service.name.upper():^8}][/] {line}")

            # 检测端口并打开浏览器
            if service.open_browser_hint and self.auto_open_browser and not self._browser_opened:
                match = port_regex.search(line)
                if match:
                    url = f"http://localhost:{match.group(1)}"
                    await self._safe_print(f"[bold blue]🌐 Opening browser:  {url}[/bold blue]")
                    try:
                        webbrowser.open_new_tab(url)
                        self._browser_opened = True
                    except Exception:
                        await self._safe_print("[yellow]⚠️ Could not open browser[/yellow]")

    async def _monitor_health(self, service: ServiceConfig):
        """监控服务健康状态"""
        assert service.health_check_url is not None
        if await self._health_check(service.health_check_url):
            await self._safe_print(f"[bold green]✓ {service.name} is healthy![/bold green]")
            self.ready_events[service.name].set()
        else:
            await self._safe_print(f"[bold red]❌ {service.name} health check failed[/bold red]")
            self._shutdown_event.set()

    async def shutdown(self):
        """优雅关闭所有服务"""
        self._shutdown_event.set()
        await self._safe_print("\n[bold yellow]🛑 Shutting down all services.. .[/bold yellow]")

        # 逆序关闭（先关闭依赖者）
        for name in reversed(list(self.processes.keys())):
            proc = self.processes[name]
            if proc.returncode is None:
                await self._safe_print(f"[yellow]Stopping {name} (PID {proc.pid}).. .[/yellow]")
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                    await self._safe_print(f"[green]✓ {name} stopped[/green]")
                except asyncio.TimeoutError:
                    await self._safe_print(f"[red]Force killing {name}.. .[/red]")
                    proc.kill()
                    await proc.wait()
                    await self._safe_print(f"[green]✓ {name} killed[/green]")

        # 清理临时目录
        for td in _TEMP_DIRS:
            try:
                td.cleanup()
            except Exception:
                pass
        _TEMP_DIRS.clear()

        await self._safe_print("[bold blue]✓ All services stopped[/bold blue]")

    async def run_all(self, services: list[ServiceConfig]):
        """运行所有服务"""
        await self._safe_print("[bold cyan]🚀 Starting services...[/bold cyan]")

        # 设置信号处理
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        # 启动所有服务任务
        tasks = [asyncio.create_task(self._run_service(svc)) for svc in services]

        await self._safe_print("[bold green]✓ All services started[/bold green]")

        # 等待关闭事件或任意服务退出
        shutdown_task = asyncio.create_task(self._shutdown_event.wait())
        done, pending = await asyncio.wait([shutdown_task, *tasks], return_when=asyncio.FIRST_COMPLETED)

        # 确保完全关闭
        if not self._shutdown_event.is_set():
            await self.shutdown()

        # 取消剩余任务
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# --------- CLI Commands ---------


def _run_async(coro):
    """运行异步函数的辅助方法"""
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        pass


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
    # 1. 注入环境变量
    if data_dir:
        os.environ["DINGENT_HOME"] = str(data_dir.resolve())

    # 2. 导入依赖
    from dingent.cli.assets import asset_manager
    from dingent.core.paths import paths

    console.print("[cyan]🔍 Checking runtime environment.. .[/cyan]")

    # 3. 准备资源
    asset_paths = asset_manager.ensure_assets()
    node_bin = asset_paths["node_bin"]
    frontend_dir = asset_paths["frontend_dir"]
    frontend_script = asset_paths["frontend_script"]

    # 4. 构建服务配置
    if paths.is_frozen:
        backend_cmd = [sys.executable, "internal-backend", host, str(port)]
        backend_cwd = paths.bundle_dir
    else:
        backend_cmd = [
            "uvicorn",
            "dingent.server.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--reload",
        ]
        backend_cwd = paths.bundle_dir

    services: list[ServiceConfig] = [
        ServiceConfig(
            name="backend",
            command=backend_cmd,
            cwd=backend_cwd,
            color="magenta",
            env=dict(os.environ),
            health_check_url=f"http://{host}:{port}/api/v1/health",
        ),
    ]

    if not dev:
        services.append(
            ServiceConfig(
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

    # 5. 运行服务
    manager = AsyncServiceManager(auto_open_browser=not no_browser and not dev)
    _run_async(manager.run_all(services))


@app.command(hidden=True)
def internal_backend(host: str, port: int):
    """(Internal) 仅供打包后调用"""
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
    console.print(f"Dingent version:  {ver}")


@app.callback(invoke_without_command=True)
def main_entry(ctx: typer.Context):
    """Dingent Agent Framework CLI"""
    if ctx.invoked_subcommand is None:
        run(no_browser=False)


def main():
    app()


if __name__ == "__main__":
    main()
