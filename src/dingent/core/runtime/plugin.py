from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from fastmcp import Client, FastMCP
from fastmcp.client import SSETransport, StreamableHttpTransport, UvStdioTransport
from pydantic import BaseModel, Field, SecretStr, create_model

from ..schemas import PluginConfigSchema, PluginManifest


def _create_dynamic_config_model(
    plugin_name: str,
    config_schema: list[PluginConfigSchema],
) -> type[BaseModel]:
    field_definitions: dict[str, Any] = {}
    type_map = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "float": float,
        "bool": bool,
    }
    for item in config_schema:
        field_name = item.name
        field_type = type_map.get(item.type, str)
        if item.secret:
            field_type = SecretStr
        if item.required:
            field_info = Field(..., description=item.description)
        else:
            field_info = Field(default=item.default, description=item.description)
        field_definitions[field_name] = (field_type, field_info)
    DynamicConfigModel = create_model(
        f"{plugin_name.capitalize()}ConfigModel",
        **field_definitions,
    )
    return DynamicConfigModel


class PluginRuntime:
    mcp_client: Client
    name: str
    config: dict[str, Any] | None = None
    manifest: "PluginManifest"
    _transport: StreamableHttpTransport | UvStdioTransport | None = None
    _mcp: FastMCP | None
    _status: Literal["active", "inactive", "error"] = "inactive"

    def __init__(
        self,
        name: str,
        mcp_client: Client,
        status: Literal["active", "inactive", "error"],
        manifest: "PluginManifest",
        mcp: FastMCP | None = None,
        transport=None,
    ):
        self.name = name
        self.mcp_client = mcp_client
        self._mcp = mcp
        self._status = status
        self.manifest = manifest
        self._transport = transport

    @classmethod
    async def create_singleton(cls, manifest: "PluginManifest", log_method: Callable) -> "PluginRuntime":
        """Create a singleton PluginRuntime instance without user-specific configuration."""
        env = {}

        if manifest.config_schema:
            pass
            _create_dynamic_config_model(manifest.display_name, manifest.config_schema)

        if manifest.execution.mode == "remote":
            assert manifest.execution.url is not None
            if manifest.execution.url.endswith("sse"):
                transport = SSETransport(url=manifest.execution.url, headers=env)
            else:
                transport = StreamableHttpTransport(url=manifest.execution.url, headers=env, auth="oauth")
            remote_proxy = FastMCP.as_proxy(transport)
        else:
            assert manifest.execution.script_path
            module_path = ".".join(Path(manifest.execution.script_path).with_suffix("").parts)
            transport = UvStdioTransport(
                module_path,
                module=True,
                project_directory=manifest.path.as_posix(),
                env_vars=env,
                python_version=manifest.python_version,
            )
            remote_proxy = FastMCP.as_proxy(transport)

        _status = "inactive"
        try:
            await remote_proxy.get_tools()
            _status = "active"
        except Exception as e:
            _status = "error"
            log_method(
                "error",
                "Failed to connect to MCP server: {error_msg}",
                context={"plugin": manifest.display_name, "error_msg": f"{e}"},
            )

        mcp_client = Client(remote_proxy)

        instance = cls(
            name=manifest.display_name,
            mcp_client=mcp_client,
            status=_status,
            manifest=manifest,
            transport=transport,
        )
        return instance

    async def aclose(self):
        if self._transport:
            await self._transport.close()
        await self.mcp_client.close()

    @property
    def status(self):
        return self._status

    async def list_tools(self):
        async with self.mcp_client as client:
            return await client.list_tools()

    # def get_config_details(self) -> list[ConfigItemDetail]:
    #     if not self.manifest or not self.manifest.config_schema:
    #         return []
    #     details = []
    #     for schema_item in self.manifest.config_schema:
    #         current_value = (self.config or {}).get(schema_item.name)
    #         is_secret = getattr(schema_item, "secret", False)
    #         if is_secret and current_value is not None:
    #             display_value = "********"
    #         else:
    #             display_value = current_value
    #         item_detail = ConfigItemDetail(
    #             name=schema_item.name,
    #             type=schema_item.type,
    #             description=schema_item.description,
    #             required=schema_item.required,
    #             secret=is_secret,
    #             default=schema_item.default,
    #             value=display_value,
    #         )
    #         details.append(item_detail)
    #     return details
