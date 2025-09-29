from fastmcp import Client, FastMCP
from fastmcp.client import SSETransport, StreamableHttpTransport, UvStdioTransport
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal
from fastmcp.server.middleware import Middleware
from fastmcp.tools import Tool
from pydantic import ValidationError

from collections.abc import Callable
from typing import Any

from fastmcp.server.middleware import Middleware
from pydantic import BaseModel, Field, SecretStr, create_model

from dingent.core.db.models import AssistantPluginLink

from dingent.core.db.models import AssistantPluginLink
from ..schemas import PluginManifest, ConfigItemDetail, PluginConfigSchema


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
    _mcp: FastMCP
    _status: Literal["active", "inactive", "error"] = "inactive"

    def __init__(
        self,
        name: str,
        mcp_client: Client,
        mcp: FastMCP,
        status: Literal["active", "inactive", "error"],
        manifest: "PluginManifest",
        config: dict[str, Any] | None = None,
        transport=None,
    ):
        self.name = name
        self.mcp_client = mcp_client
        self._mcp = mcp
        self._status = status
        self.config = config
        self.manifest = manifest
        self._transport = transport

    @classmethod
    async def from_config(
        cls,
        manifest: "PluginManifest",
        link: AssistantPluginLink,
        log_method: Callable,
        middleware: Middleware | None = None,
    ) -> "PluginRuntime":
        """ """
        env = {}
        validated_config_dict = {}

        if manifest.config_schema:
            DynamicConfigModel = _create_dynamic_config_model(manifest.name, manifest.config_schema)
            try:
                validated_model = DynamicConfigModel.model_validate(link.user_config_values or {})
                validated_config_dict = validated_model.model_dump(mode="json")
                env = _prepare_environment(validated_model)
            except ValidationError as e:
                log_method("warning", "Configuration validation error for plugin '{plugin}': {error_msg}", context={"plugin": manifest.name, "error_msg": f"{e}"})
                validated_config_dict = link.user_config_values or {}

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
                context={"plugin": manifest.name, "error_msg": f"{e}"},
            )

        mcp = FastMCP(name=manifest.name)
        mcp.mount(remote_proxy)
        if middleware:
            mcp.add_middleware(middleware)

        base_tools_dict = await mcp.get_tools()

        for tool in link.tool_configs or []:
            base_tool = base_tools_dict.get(tool.name)
            if not base_tool:
                continue
            log_method("info", "Translating tool '{tool}' to user config", context={"tool": tool.name})
            trans_tool = Tool.from_tool(base_tool, name=tool.name, description=tool.description, enabled=tool.enabled)
            mcp.add_tool(trans_tool)
            if tool.name != base_tool.name:
                mirrored_tool = base_tool.copy()
                mirrored_tool.disable()
                mcp.add_tool(mirrored_tool)

        mcp_client = Client(mcp)

        instance = cls(
            name=manifest.name,
            mcp_client=mcp_client,
            mcp=mcp,
            status=_status,
            config=validated_config_dict,
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
        return await self._mcp.get_tools()

    def get_config_details(self) -> list[ConfigItemDetail]:
        if not self.manifest or not self.manifest.config_schema:
            return []
        details = []
        for schema_item in self.manifest.config_schema:
            current_value = (self.config or {}).get(schema_item.name)
            is_secret = getattr(schema_item, "secret", False)
            if is_secret and current_value is not None:
                display_value = "********"
            else:
                display_value = current_value
            item_detail = ConfigItemDetail(
                name=schema_item.name,
                type=schema_item.type,
                description=schema_item.description,
                required=schema_item.required,
                secret=is_secret,
                default=schema_item.default,
                value=display_value,
            )
            details.append(item_detail)
        return details
