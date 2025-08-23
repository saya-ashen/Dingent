"""
Dingent CLI (含前端 + 后端并发运行的精简版)

命令:
  dingent run       并发启动 backend(langgraph dev 无UI) + frontend(node)
  dingent dev       启动带 UI 的 langgraph dev (仅后端，调试 Graph + API)
  dingent init      从模板创建一个新的 Agent 项目
  dingent version   显示版本

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
DEFAULT_API_SPEC = "dingent.server.main:app"
ENV_GRAPH_SPEC = "DINGENT_GRAPH_SPEC"
ENV_API_SPEC = "DINGENT_API_SPEC"

PROD_REPO_URL = "https://github.com/saya-ashen/Dingent.git"
# 如果在开发模式下运行，可以指向本地仓库以方便调试
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

# --------- 工具函数 ---------


def _ensure_project_root(cli_ctx: CliContext) -> CliContext:
    """
    检查当前目录是否为 Dingent 项目，如果不是，则提示用户创建 dingent.toml。
    """
    if not cli_ctx.project_root:
        print("[bold yellow]⚠️ 当前目录不是一个 Dingent 项目 (缺少 dingent.toml)。[/bold yellow]")
        create_file = typer.confirm("你希望在这里创建一个默认的 dingent.toml 配置文件吗？")
        if create_file:
            cwd = Path.cwd()
            project_name = cwd.name
            config_path = cwd / "dingent.toml"
            config_content = DEFAULT_DINGENT_TOML.format(project_name=project_name)
            config_path.write_text(config_content, encoding="utf-8")
            print(f"[bold green]✅ 已在 {config_path} 创建默认配置文件，请重新运行命令启动[/bold green]")
            raise typer.Exit()
        else:
            print("[bold red]操作已取消。[/bold red]")
            raise typer.Exit()
    return cli_ctx


def _resolve_node_binary() -> str:
    """
    使用 nodejs_wheel 获取 node 可执行路径。
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
    生成后端 langgraph.dev 使用的临时配置文件。
    返回配置文件路径。
    """
    graph_spec = os.getenv(ENV_GRAPH_SPEC, DEFAULT_GRAPH_SPEC)
    api_spec = os.getenv(ENV_API_SPEC, DEFAULT_API_SPEC)
    td = tempfile.TemporaryDirectory()
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


class ProjectInitializer:
    """处理 'init' 命令的逻辑。"""

    def __init__(self, project_name, template, checkout):
        self.project_name = project_name
        self.template = template
        self.checkout = checkout
        self.project_path = None

    def run(self):
        """执行整个项目初始化工作流。"""
        try:
            self._create_from_template()
            self._print_final_summary()
        except RepositoryNotFound:
            print(f"[bold red]\n❌ 错误: 仓库未找到 {REPO_URL}[/bold red]")
            print("[bold red]\n请检查 URL 和你的网络连接。[/bold red]")
            raise typer.Exit()
        except Exception as e:
            print(f"[bold red]\n发生意外错误: {e}[/bold red]")
            raise typer.Exit()

    def _create_from_template(self):
        """使用 Cookiecutter 构建项目。"""
        print(f"[bold green]🚀 从 Git 仓库初始化项目: {REPO_URL}[/bold green]")
        template_dir = f"templates/{self.template}"
        created_path = cookiecutter(
            REPO_URL,
            directory=template_dir,
            checkout=self.checkout,
            extra_context={"project_slug": self.project_name},
            output_dir=".",
        )
        self.project_path = Path(created_path)
        print(f"[bold green]✅ 项目已创建于 {self.project_path}[/bold green]")

    def _print_final_summary(self):
        """打印最终的成功信息和后续步骤。"""
        final_project_name = self.project_path.name
        print("[bold green]\n🎉 项目初始化成功！[/bold green]")
        print("\n后续步骤:")
        print(f"  1. 进入项目目录: cd {final_project_name}")
        print("  2. 启动所有服务: dingent run")


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

        t = threading.Thread(target=self._log_loop, daemon=True)
        t.start()

        print("[bold green]✓ 所有服务已启动，实时日志如下 (Ctrl+C 退出)[/bold green]")
        try:
            while not self._stop_event.is_set():
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
    """
    if proc.poll() is not None:
        return

    print(f"[yellow]停止 {name} (PID {proc.pid}) ...[/yellow]", end="")

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
        print("[green] ✓ (已结束)[/green]")
    except Exception as e:
        print(f"[red] 失败: {e}[/red]")


# --------- Commands ---------
@app.command()
def run(
    no_browser: bool = typer.Option(False, "--no-browser", help="不自动打开前端页面"),
):
    """
    并发启动 backend 和 frontend 服务。
    """
    cli_ctx = CliContext()
    cli_ctx = _ensure_project_root(cli_ctx)

    cfg_path = _make_backend_temp_config()
    try:
        node_bin = _resolve_node_binary()
    except Exception as e:
        print(f"[bold red]❌ 解析 Node 失败: {e}[/bold red]")
        raise typer.Exit(1)

    backend_cmd = [
        "langgraph",
        "dev",
        "--no-browser",
        "--allow-blocking",
        "--host",
        "127.0.0.1",
        "--port",
        str(cli_ctx.backend_port),
        "--config",
        str(cfg_path),
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
            env={"DING_BACKEND_URL": f"http://127.0.0.1:{cli_ctx.backend_port}"},
            open_browser_hint=True,
        ),
    ]

    supervisor = ServiceSupervisor(services, auto_open_frontend=not no_browser)
    supervisor.start_all()


@app.command()
def dev(
    open_ui: bool = typer.Option(True, "--ui/--no-ui", help="启动官方 langgraph dev UI"),
    with_frontend: bool = typer.Option(True, "--with-frontend", help="同时启动前端"),
    no_browser: bool = typer.Option(False, "--no-browser", help="当 --with-frontend 启用时不自动打开浏览器"),
):
    """
    启动开发服务，主要用于调试后端 Graph 和 API。
    """
    if not open_ui and not with_frontend:
        print("[yellow]未指定任何操作 (请使用 --ui 或 --with-frontend)，已退出。[/yellow]")
        raise typer.Exit(0)

    cli_ctx = CliContext()
    cli_ctx = _ensure_project_root(cli_ctx)

    if open_ui and not with_frontend:
        try:
            from .dev_runner import start_langgraph_ui
        except Exception as e:
            print(f"[bold red]导入 dev_runner 失败: {e}[/bold red]")
            raise typer.Exit(1)
        start_langgraph_ui()
        return

    cfg_path = _make_backend_temp_config()
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
            color="magenta",
            open_browser_hint=True,
        ),
    ]

    if with_frontend:
        try:
            node_bin = _resolve_node_binary()
        except Exception as e:
            print(f"[bold red]❌ 解析 Node 失败: {e}[/bold red]")
            raise typer.Exit(1)

        frontend_cmd = [node_bin, "server.js", "--port", str(cli_ctx.frontend_port)]
        services.append(
            Service(
                name="frontend",
                command=frontend_cmd,
                cwd=cli_ctx.frontend_path,
                color="cyan",
                env={"DING_BACKEND_URL": f"http://127.0.0.1:{cli_ctx.backend_port}"},
            )
        )

    supervisor = ServiceSupervisor(services, auto_open_frontend=not no_browser)
    supervisor.start_all()


@app.command("init")
def init(
    project_name: Annotated[str, typer.Argument(help="新项目的名称")],
    template: Annotated[str, typer.Option(help="用于创建项目的模板")] = "basic",
    checkout: Annotated[str, typer.Option(help="要检出的分支、标签或提交")] = "main",
):
    """从模板创建一个新的 Agent 项目。"""
    initializer = ProjectInitializer(project_name, template, checkout)
    initializer.run()


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


if __name__ == "__main__":
    main()
