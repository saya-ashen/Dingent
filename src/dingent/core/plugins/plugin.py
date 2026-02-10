from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastmcp import Client, FastMCP
from fastmcp.mcp_config import MCPConfig

from .schemas import PluginManifest


class PluginRuntime:
    mcp_client: Client
    name: str
    id: str
    manifest: "PluginManifest"
    _status: Literal["active", "inactive", "error"] = "inactive"

    def __init__(
        self,
        name: str,
        id: str,
        mcp_client: Client,
        status: Literal["active", "inactive", "error"],
        manifest: "PluginManifest",
        mcp: FastMCP | None = None,
    ):
        self.name = name
        self.mcp_client = mcp_client
        self._status = status
        self.manifest = manifest
        self.id = id

    @classmethod
    async def create_singleton(cls, manifest: "PluginManifest", log_method: Callable) -> "PluginRuntime":
        """Create a singleton PluginRuntime instance without user-specific configuration."""
        project_root = str(Path(manifest.path).resolve())

        for _, server in manifest.servers.items():
            command = getattr(server, "command", None)
            original_args = getattr(server, "args", [])

            # 1. 先处理路径解析 (使用上面的逻辑)
            resolved_args = []
            for arg in original_args:
                candidate = Path(project_root) / arg
                if not arg.startswith("-") and not Path(arg).is_absolute() and candidate.is_file():
                    resolved_args.append(str(candidate))
                else:
                    resolved_args.append(arg)

            # 2. 注入 --project (针对 uv)
            # 检查是否是 uv 命令
            if resolved_args and command == "uv" and "--project" not in resolved_args:
                # 找到 'run' 的位置，如果存在的话
                try:
                    run_index = resolved_args.index("run")
                    # 在 'run' 后面插入 --project <path>
                    # 最终变成: uv run --project /abs/path script.py
                    resolved_args.insert(run_index + 1, project_root)
                    resolved_args.insert(run_index + 1, "--project")
                except ValueError:
                    pass

            server.args = resolved_args

        client = Client(MCPConfig(mcpServers=manifest.servers))

        _status = "inactive"
        try:
            async with client as mcp_client:
                await mcp_client.list_tools()
            _status = "active"
        except Exception as e:
            _status = "error"
            log_method(
                "error",
                "Failed to connect to MCP server: {error_msg}",
                context={"plugin": manifest.display_name, "error_msg": f"{e}"},
            )

        instance = cls(
            name=manifest.display_name,
            id=manifest.id,
            mcp_client=client,
            status=_status,
            manifest=manifest,
        )
        return instance

    async def aclose(self):
        await self.mcp_client.close()

    @property
    def status(self):
        return self._status

    async def list_tools(self):
        async with self.mcp_client as client:
            return await client.list_tools()
