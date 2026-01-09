from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastmcp import Client, FastMCP
from fastmcp.mcp_config import MCPConfig

from .schemas import PluginManifest


class PluginRuntime:
    mcp_client: Client
    name: str
    manifest: "PluginManifest"
    _status: Literal["active", "inactive", "error"] = "inactive"

    def __init__(
        self,
        name: str,
        mcp_client: Client,
        status: Literal["active", "inactive", "error"],
        manifest: "PluginManifest",
        mcp: FastMCP | None = None,
    ):
        self.name = name
        self.mcp_client = mcp_client
        self._status = status
        self.manifest = manifest

    @classmethod
    async def create_singleton(cls, manifest: "PluginManifest", log_method: Callable) -> "PluginRuntime":
        """Create a singleton PluginRuntime instance without user-specific configuration."""
        for _, server in manifest.servers.items():
            args: list[str] = getattr(server, "args", [])
            for i, arg in enumerate(args):
                if arg.endswith((".py", ".js")) and not Path(arg).is_absolute():
                    args[i] = str(Path(manifest.path) / arg)
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
