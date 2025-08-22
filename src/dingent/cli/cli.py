"""
Dingent CLI (含前端 + 后端并发运行的精简版)

命令:
  dingent run        并发启动 backend(langgraph dev 无UI) + frontend(node)
  dingent dev        启动带 UI 的 langgraph dev (仅后端，调试 Graph + API)
  dingent version    显示版本

可选环境变量:
  DINGENT_GRAPH_SPEC  覆盖默认 Graph 入口 (默认: dingent.engine.graph:make_graph)
  DINGENT_API_SPEC    覆盖默认 FastAPI 应用入口 (默认: dingent.server.main:app)
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

import psutil
import typer
from rich import print
from rich.text import Text

from .context import CliContext

app = typer.Typer(help="Dingent Agent Framework CLI")

DEFAULT_GRAPH_SPEC = "dingent.engine.graph:make_graph"
DEFAULT_API_SPEC = "dingent.server.main:app"
ENV_GRAPH_SPEC = "DINGENT_GRAPH_SPEC"
ENV_API_SPEC = "DINGENT_API_SPEC"


# --------- 工具函数 ---------
def _resolve_node_binary() -> str:
    """
    使用 nodejs_wheel 获取 node 可执行路径。
    你之前使用 nodejs_wheel.node()，这里复用思路。
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
        raise RuntimeError("nodejs_wheel 返回异常")
    except Exception as e:
        raise RuntimeError(f"无法解析 Node 可执行文件: {e}")


def _make_backend_temp_config() -> Path:
    """
    生成后端 langgraph.dev 使用的临时配置文件（无 UI 模式）。
    返回配置文件路径。
    """
    graph_spec = os.getenv(ENV_GRAPH_SPEC, DEFAULT_GRAPH_SPEC)
    api_spec = os.getenv(ENV_API_SPEC, DEFAULT_API_SPEC)
    td = tempfile.TemporaryDirectory()  # 不立即释放，挂到全局列表防止 GC
    _TEMP_DIRS.append(td)
    cfg_path = Path(td.name) / "langgraph.json"
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


_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []  # 防止被 GC 清理


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
        print("[bold cyan]🚀 启动服务...[/bold cyan]")
        for svc in self.services:
            self._start_service(svc)

        # 启动日志线程
        t = threading.Thread(target=self._log_loop, daemon=True)
        t.start()

        print("[bold green]✓ 所有服务已启动，实时日志如下 (Ctrl+C 退出)[/bold green]")
        try:
            while not self._stop_event.is_set():
                # 检查存活
                for svc in self.services:
                    if svc.process and svc.process.poll() is not None:
                        print(f"\n[bold red]服务 {svc.name} 已退出，代码 {svc.process.returncode}，准备关闭其它服务...[/bold red]")
                        self.stop_all()
                        raise typer.Exit(1)
                time.sleep(0.3)
        except KeyboardInterrupt:
            if not hasattr(self, "_shutting_down"):
                self._shutting_down = True
                print("\n[bold yellow]收到中断信号，正在关闭服务 (再次 Ctrl+C 将强制退出)...[/bold yellow]")
                try:
                    self.stop_all()
                except KeyboardInterrupt:
                    print("\n[bold red]二次中断：立即强制终止所有进程[/bold red]")
                    self.stop_all(force=True)
            else:
                print("\n[bold red]再次收到中断，强制终止...[/bold red]")
                self.stop_all(force=True)

    def stop_all(self, force: bool = False):
        self._stop_event.set()
        for svc in reversed(self.services):
            if svc.process and svc.process.poll() is None:
                _terminate_process_tree(svc.process, svc.name, force=force)
        print("[bold blue]🛑 所有进程已结束[/bold blue]")

        # 新增：清理临时目录（防止GC不及时，导致下次端口占用）
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
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        try:
            svc.process = subprocess.Popen(svc.command, **popen_kwargs)  # noqa: S603
        except FileNotFoundError:
            print(f"[bold red]❌ 启动 {svc.name} 失败：命令不存在: {svc.command[0]}[/bold red]")
            raise typer.Exit(1)
        threading.Thread(target=self._stream_reader, args=(svc,), daemon=True).start()
        print(f"[bold green]✓ {svc.name} (PID {svc.process.pid}) 已启动: {' '.join(svc.command)}[/bold green]")

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

            # 自动打开前端
            if svc and svc.open_browser_hint and self.auto_open_frontend and not self._browser_opened:
                m = port_regex.search(line)
                if m:
                    url = f"http://localhost:{m.group(1)}"
                    print(f"[bold blue]🌐 打开浏览器: {url}[/bold blue]")
                    try:
                        webbrowser.open_new_tab(url)
                        self._browser_opened = True
                    except Exception:
                        print("[yellow]⚠️ 无法自动打开浏览器[/yellow]")


def _terminate_process_tree(proc: subprocess.Popen, name: str, force: bool = False):
    """
    使用 psutil 递归终止进程及其所有后代进程。
    先尝试 graceful terminate (等效SIGTERM)，超时后 force kill (等效SIGKILL)。
    """
    if proc.poll() is not None:
        return

    print(f"[yellow]停止 {name} (PID {proc.pid}) ...[/yellow]", end="")

    try:
        # 获取主进程
        main_proc = psutil.Process(proc.pid)

        # 获取所有后代进程（递归）
        children = main_proc.children(recursive=True)

        # 先尝试 graceful terminate（发送SIGTERM等效）
        if not force:
            main_proc.terminate()
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass

            # 等待（最多8秒）
            gone, alive = psutil.wait_procs([main_proc] + children, timeout=8)
            if not alive:
                print("[green] ✓[/green]")
                return

        # 如果超时或force，直接kill
        main_proc.kill()
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass

        # 等待确认（最多5秒）
        psutil.wait_procs([main_proc] + children, timeout=5)
        print("[yellow] (force/kill) ✓[/yellow]")

    except psutil.NoSuchProcess:
        print("[green] ✓ (已结束)[/green]")
    except Exception as e:
        print(f"[red] 失败: {e}[/red]")


# --------- Commands ---------
@app.command()
def run(
    no_browser: bool = typer.Option(False, "--no-browser", help="不自动打开前端页面"),
):
    """
    并发启动:
      - backend: langgraph dev (无浏览器) 使用内置 Graph + API 临时配置
      - frontend: node server.js
    """
    cli_ctx = CliContext()
    if not cli_ctx.project_root:
        print("[bold red]❌ 当前目录不是 Dingent 项目（缺少 dingent.toml）[/bold red]")
        raise typer.Exit(1)

    # 生成临时 config
    cfg_path = _make_backend_temp_config()

    # 解析 node
    try:
        node_bin = _resolve_node_binary()
    except Exception as e:
        print(f"[bold red]❌ 解析 Node 失败: {e}[/bold red]")
        raise typer.Exit(1)

    # 构建服务
    backend_cmd = [
        "langgraph",
        "dev",
        "--no-browser",
        "--allow-blocking",
        "--host",
        "127.0.0.1",  # 新增：显式绑定localhost，减少风险
        "--port",
        str(cli_ctx.backend_port),
        "--config",
        str(cfg_path),
    ]
    frontend_cmd = [
        node_bin,
        "server.js",
        "--port",
        str(cli_ctx.frontend_port),
    ]
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
            cwd=cli_ctx.project_root,
            color="cyan",
            env={"DING_BACKEND_URL": f"http://127.0.0.1:{cli_ctx.backend_port}"},
            open_browser_hint=True,
        ),
    ]

    supervisor = ServiceSupervisor(services, auto_open_frontend=not no_browser)
    supervisor.start_all()


@app.command()
def dev(
    open_ui: bool = typer.Option(True, "--ui/--no-ui", help="启动官方 langgraph dev UI"),
    with_frontend: bool = typer.Option(True, "--with-frontend", help="同时启动前端(简单后台日志合并)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="与 --with-frontend 一起使用时不自动开浏览器"),
):
    if not open_ui and not with_frontend:
        print("[yellow]未指定任何操作(加 --ui 或 --with-frontend)；退出。[/yellow]")
        raise typer.Exit(0)

    cli_ctx = CliContext()

    if open_ui and not with_frontend:
        # 直接使用 dev_runner (阻塞)
        try:
            from .dev_runner import start_langgraph_ui
        except Exception as e:
            print(f"[bold red]导入 dev_runner 失败: {e}[/bold red]")
            raise typer.Exit(1)
        start_langgraph_ui()
        return

    # 启动 UI 和前端：UI 作为一个服务（--allow-blocking 避免后台阻塞）
    cfg_path = _make_backend_temp_config()
    backend_cmd = [
        "langgraph",
        "dev",
        "--allow-blocking",
        "--port",
        str(cli_ctx.backend_port),
        "--config",
        str(cfg_path),
    ]
    try:
        node_bin = _resolve_node_binary()
    except Exception as e:
        print(f"[bold red]❌ 解析 Node 失败: {e}[/bold red]")
        raise typer.Exit(1)
    frontend_cmd = [
        node_bin,
        "server.js",
        "--port",
        str(cli_ctx.frontend_port),
    ]
    services = [
        Service(
            name="backend-ui" if open_ui else "backend",
            command=backend_cmd,
            cwd=cli_ctx.project_root,
            color="magenta",
            open_browser_hint=True,
        ),
        Service(
            name="frontend",
            command=frontend_cmd,
            cwd=cli_ctx.frontend_path,
            color="cyan",
            env={"DING_BACKEND_URL": f"http://127.0.0.1:{cli_ctx.backend_port}"},
        ),
    ]
    supervisor = ServiceSupervisor(services, auto_open_frontend=not no_browser)
    supervisor.start_all()


@app.command()
def version():
    """显示 Dingent 版本"""
    try:
        from importlib.metadata import version as _v

        ver = _v("dingent")
    except Exception:
        ver = "unknown"
    print(f"Dingent version: {ver}")


def main():
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
