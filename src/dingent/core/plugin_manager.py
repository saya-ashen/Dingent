import json
import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import toml
from fastmcp import Client, FastMCP
from fastmcp.client import SSETransport, StreamableHttpTransport, UvStdioTransport
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import Tool
from fastmcp.tools.tool import ToolResult as FastMCPToolResult
from mcp.types import TextContent
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, ValidationError, create_model

from dingent.core.log_manager import LogManager

from .resource_manager import ResourceManager
from .types import (
    ConfigItemDetail,
    ExecutionModel,
    PluginBase,
    PluginConfigSchema,
    PluginUserConfig,
    ToolResult,
)

LOGGING_LEVEL_MAP = logging.getLevelNamesMapping()


class ResourceMiddleware(Middleware):
    """
    拦截工具调用结果，标准化为 ToolResult，并存储，仅向模型暴露最小必要文本。
    """

    def __init__(self, resource_manager: ResourceManager, log_method: Callable):
        super().__init__()
        self.resource_manager = resource_manager
        self.log_with_context = log_method

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        result = await call_next(context)

        assert context.fastmcp_context

        # 1. 抽取原始返回
        raw_text = ""
        if result.content and result.content[0].text:
            raw_text = result.content[0].text

        structured = result.structured_content
        parsed_obj: Any = None

        # 2. 尝试解析 JSON
        if structured and isinstance(structured, dict):
            parsed_obj = structured
        else:
            if raw_text:
                try:
                    parsed_obj = json.loads(raw_text)
                except Exception:
                    parsed_obj = raw_text
            else:
                parsed_obj = raw_text

        # 3. 标准化为 ToolResult
        try:
            tool_result = ToolResult.from_any(parsed_obj)
        except Exception as e:
            self.log_with_context("warning", "Failed to parse tool result: {error_msg}", context={"error_msg": f"{e}"})
            tool_result = ToolResult.from_any(raw_text)

        # 4. 注册资源
        artifact_id = self.resource_manager.register(tool_result)

        # 5. 构建最小结构，喂给模型的文本直接用 model_text
        minimal_struct = {
            "artifact_id": artifact_id,
            "model_text": tool_result.model_text,
            "version": tool_result.version,
        }

        # 6. 覆盖返回
        result.structured_content = minimal_struct
        # 给模型的自然语言部分：只放 model_text，避免输出 JSON 杂讯
        if result.content:
            result.content[0].text = tool_result.model_text
        else:
            # 部分 fastmcp 实现可能需要确保 content 不为空

            result.content = [
                FastMCPToolResult(content=TextContent(type="text", text=tool_result.model_text)),
            ]

        return result


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


def _prepare_environment(validated_config: BaseModel) -> dict[str, str]:
    env_vars = {}
    for field_name, value in validated_config.model_dump().items():
        if value is None:
            continue
        if isinstance(getattr(validated_config, field_name), SecretStr):
            secret_value = getattr(validated_config, field_name).get_secret_value()
            env_vars[field_name] = secret_value
        else:
            env_vars[field_name] = str(value)
    return env_vars


class PluginInstance:
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
        user_config: PluginUserConfig,
        log_method: Callable,
        middleware: Middleware | None = None,
    ) -> "PluginInstance":
        if not user_config.enabled:
            raise ValueError(f"Plugin '{manifest.name}' is not enabled. This should not happend")
        env = {}
        validated_config_dict = {}

        if manifest.config_schema:
            DynamicConfigModel = _create_dynamic_config_model(manifest.name, manifest.config_schema)
            try:
                validated_model = DynamicConfigModel.model_validate(user_config.config or {})
                validated_config_dict = validated_model.model_dump(mode="json")
                env = _prepare_environment(validated_model)
            except ValidationError as e:
                log_method("warning", "Configuration validation error for plugin '{plugin}': {error_msg}", context={"plugin": manifest.name, "error_msg": f"{e}"})
                validated_config_dict = user_config.config or {}

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

        if not user_config.tools_default_enabled:
            for tool in base_tools_dict.values():
                mirrored_tool = tool.copy()
                mirrored_tool.disable()
                mcp.add_tool(mirrored_tool)

        for tool in user_config.tools or []:
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


class PluginManifest(PluginBase):
    id: str = Field(default="no_name_plugin", description="插件唯一标识符")
    spec_version: str | float = Field("2.0", description="插件规范版本 (遵循语义化版本)")
    execution: ExecutionModel
    dependencies: list[str] | None = None
    python_version: str | None = None
    config_schema: list[PluginConfigSchema] | None = None
    _plugin_path: Path | None = PrivateAttr(default=None)

    @classmethod
    def from_toml(cls, toml_path: Path) -> "PluginManifest":
        if not toml_path.is_file():
            raise FileNotFoundError(f"'plugin.toml' not found at '{toml_path}'")

        plugin_dir = toml_path.parent
        pyproject_toml_path = plugin_dir / "pyproject.toml"

        base_meta = {}
        if pyproject_toml_path.is_file():
            pyproject_data = toml.load(pyproject_toml_path)
            project_section = pyproject_data.get("project", {})
            valid_keys = cls.model_fields.keys()
            base_meta = {k: v for k, v in project_section.items() if k in valid_keys}

        plugin_info = toml.load(toml_path)
        plugin_meta = plugin_info.get("plugin", {})
        final_meta = base_meta | plugin_meta

        manifest = cls(**final_meta)
        manifest._plugin_path = plugin_dir
        return manifest

    @property
    def path(self) -> Path:
        if self._plugin_path is None:
            raise AttributeError("Plugin path has not been set.")
        return self._plugin_path

    async def create_instance(
        self,
        user_config: PluginUserConfig,
        log_method: Callable,
        middleware: Middleware | None = None,
    ) -> "PluginInstance":
        if self.path is None:
            raise ValueError("Plugin path is not set. Please set the path before creating an instance.")
        return await PluginInstance.from_config(
            manifest=self,
            user_config=user_config,
            middleware=middleware,
            log_method=log_method,
        )


class PluginManager:
    plugins: dict[str, PluginManifest] = {}

    def __init__(self, plugin_dir: Path, resource_manager: ResourceManager, log_manager: LogManager):
        self.plugin_dir = plugin_dir
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.log_manager = log_manager
        self.log_manager.log_with_context("info", "PluginManager initialized with plugin directory: {dir}", context={"dir": str(self.plugin_dir)})
        self._scan_and_register_plugins()
        self.middleware = ResourceMiddleware(resource_manager, self.log_manager.log_with_context)

    def _scan_and_register_plugins(self):
        if not self.plugin_dir.is_dir():
            self.log_manager.log_with_context("warning", "Plugin directory '{dir}' not found.", context={"dir": str(self.plugin_dir)})
            return

        for plugin_path in self.plugin_dir.iterdir():
            if not plugin_path.is_dir():
                self.log_manager.log_with_context("warning", "Skipping '{path}' as it is not a directory.", context={"path": str(plugin_path)})
                continue
            toml_path = plugin_path / "plugin.toml"
            if not toml_path.is_file():
                self.log_manager.log_with_context("warning", "Skipping '{path}' as 'plugin.toml' is missing.", context={"path": str(plugin_path)})
                continue
            try:
                plugin_manifest = PluginManifest.from_toml(toml_path)
                self.plugins[plugin_manifest.id] = plugin_manifest
            except Exception as e:
                self.log_manager.log_with_context("error", "Failed to load plugin from '{path}': {error_msg}", context={"path": str(toml_path), "error_msg": f"{e}"})

    def list_plugins(self) -> dict[str, PluginManifest]:
        return self.plugins

    async def create_instance(self, instance_settings: PluginUserConfig):
        plugin_id = instance_settings.plugin_id
        if plugin_id not in self.plugins:
            raise ValueError(f"Plugin '{plugin_id}' is not registered or failed to load.")
        plugin_definition = self.plugins[plugin_id]
        return await plugin_definition.create_instance(
            instance_settings,
            self.log_manager.log_with_context,
            self.middleware,
        )

    def get_plugin_manifest(self, plugin_id: str) -> PluginManifest | None:
        return self.plugins.get(plugin_id)

    def remove_plugin(self, plugin_id: str):
        if plugin_id in self.plugins:
            plugin = self.plugins[plugin_id]
            plugin_path = plugin.path
            shutil.rmtree(plugin_path)
            self.log_manager.log_with_context("info", "Plugin '{plugin}' ({id}) removed.", context={"plugin": plugin.name, "id": plugin_id})
            del self.plugins[plugin_id]
        else:
            self.log_manager.log_with_context("warning", "Plugin with ID '{id}' not found in PluginManager.", context={"id": plugin_id})

    def reload_plugins(self):
        self.plugins.clear()
        self._scan_and_register_plugins()

    def get_installed_versions(self) -> dict[str, str]:
        """
        Scans registered plugins and returns a dictionary of their IDs and versions.

        Returns:
            A dictionary mapping plugin_id to its version string.
            Example: {"my-cool-plugin": "1.2.0", "another-plugin": "0.9.1"}
        """
        if not self.plugins:
            return {}

        # Use a dictionary comprehension for a clean and efficient implementation
        return {plugin_id: str(manifest.version) for plugin_id, manifest in self.plugins.items() if manifest.version is not None}
