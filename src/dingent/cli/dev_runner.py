import json
import os
import subprocess
import tempfile
from pathlib import Path

DEFAULT_GRAPH_SPEC = "dingent.engine.graph:make_graph"
DEFAULT_API_SPEC = "dingent.server.main:app"
ENV_GRAPH_SPEC = "DINGENT_GRAPH_SPEC"
ENV_API_SPEC = "DINGENT_API_SPEC"


def _graph_spec():
    return os.getenv(ENV_GRAPH_SPEC, DEFAULT_GRAPH_SPEC)


def _api_spec():
    return os.getenv(ENV_API_SPEC, DEFAULT_API_SPEC)


def start_langgraph_ui():
    """
    启动 LangGraph 官方 dev UI：
      - 在临时目录创建 langgraph.json
      - 指向内部 Graph 与 API
      - 不污染用户项目
    """
    graph_spec = _graph_spec()
    api_spec = _api_spec()

    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "langgraph.json"
        cfg = {
            "graphs": {"agent": graph_spec},
            "http": {"app": api_spec},
            "dependencies": ["dingent"],
            "metadata": {"provider": "dingent", "mode": "dev-ui"},
        }
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[dingent] 临时配置生成: {cfg_path}")
        try:
            subprocess.run(["langgraph", "dev", "--config", str(cfg_path)], check=True)
        except FileNotFoundError:
            print("[dingent] 未找到 langgraph 可执行文件，请先安装：pip install langgraph")
        except subprocess.CalledProcessError as e:
            print(f"[dingent] 启动 langgraph dev 失败: {e}")
