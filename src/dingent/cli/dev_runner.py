import json
import os
import subprocess
import tempfile
from pathlib import Path

from rich import print

DEFAULT_GRAPH_SPEC = "dingent.engine.graph:make_graph"
DEFAULT_API_SPEC = "dingent.server.app_factory:app"
ENV_GRAPH_SPEC = "DINGENT_GRAPH_SPEC"
ENV_API_SPEC = "DINGENT_API_SPEC"


def _graph_spec():
    return os.getenv(ENV_GRAPH_SPEC, DEFAULT_GRAPH_SPEC)


def _api_spec():
    return os.getenv(ENV_API_SPEC, DEFAULT_API_SPEC)


def start_langgraph_ui():
    """
    Starts the official LangGraph dev UI:
      - Creates langgraph.json in a temporary directory
      - Points to the internal Graph and API
      - Does not pollute the user's project
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
        print(f"[dingent] Temporary config generated: {cfg_path}")
        try:
            subprocess.run(["langgraph", "dev", "--config", str(cfg_path)], check=True)
        except FileNotFoundError:
            print("[dingent] 'langgraph' executable not found. Please install it first: pip install langgraph")
        except subprocess.CalledProcessError as e:
            print(f"[dingent] Failed to start langgraph dev: {e}")
