from collections.abc import Callable

from pathlib import Path
from typing import Any, Literal

from fastmcp import Client, FastMCP
from fastmcp.client import SSETransport, StreamableHttpTransport, UvStdioTransport
from fastmcp.mcp_config import MCPConfig
from pydantic import BaseModel, Field, SecretStr, create_model

from ..schemas import PluginConfigSchema, PluginManifest


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
        env = {}
        for key, server in manifest.servers.items():
            args: list[str] = getattr(server, "args", [])
            for i, arg in enumerate(args):
                if arg.endswith((".py", ".js")) and not Path(arg).is_absolute():
                    args[i] = str(Path(manifest.path) / arg)
        client = Client(MCPConfig(mcpServers=manifest.servers))

        # if manifest.execution.mode == "remote":
        #     assert manifest.execution.url is not None
        #     if manifest.execution.url.endswith("sse"):
        #         transport = SSETransport(url=manifest.execution.url, headers=env)
        #     else:
        #         transport = StreamableHttpTransport(url=manifest.execution.url, headers=env, auth="oauth")
        #     remote_proxy = FastMCP.as_proxy(transport)
        # else:
        #     assert manifest.execution.script_path
        #     module_path = ".".join(Path(manifest.execution.script_path).with_suffix("").parts)
        #     transport = UvStdioTransport(
        #         module_path,
        #         module=True,
        #         project_directory=manifest.path,
        #         env_vars=env,
        #         python_version=manifest.python_version,
        #     )
        #     remote_proxy = FastMCP.as_proxy(transport)

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
