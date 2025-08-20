import json
import logging
from pathlib import Path
from typing import Any, Literal

import toml
from fastmcp import Client, FastMCP
from fastmcp.client import SSETransport, StreamableHttpTransport, UvStdioTransport
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import Tool
from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, ValidationError, create_model

from dingent.core.log_manager import log_with_context

from .resource_manager import get_resource_manager
from .types import ConfigItemDetail, ExecutionModel, PluginConfigSchema, PluginUserConfig, ToolOutput
from .utils import find_project_root

LOGGING_LEVEL_MAP = logging.getLevelNamesMapping()


class ResourceMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        resource_manager = get_resource_manager()
        result = await call_next(context)

        assert context.fastmcp_context
        # tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)

        def pack(text: str) -> dict:
            payload = {"type": "markdown", "content": text}
            tool_output = ToolOutput(payloads=[payload])
            tool_output_id = resource_manager.register(tool_output)
            return {"context": text, "tool_output_id": tool_output_id}

        text = result.content[0].text if result.content and result.content[0].text else ""
        sc = result.structured_content
        if not sc and text:
            try:
                sc = json.loads(text)
            except Exception as e:
                logger.warning(f"Failed to parse structured content: {e}")
                sc = None

        # 有输出 schema：若包含 context + tool_outputs，注册并替换为 tool_output_id
        if isinstance(sc, dict) and {"context", "tool_outputs"}.issubset(sc.keys()):
            tool_output = ToolOutput(payloads=sc["tool_outputs"])
            tool_output_id = resource_manager.register(tool_output)
            sc = {**sc}
            sc.pop("tool_outputs", None)
            sc["tool_output_id"] = tool_output_id
            result.structured_content = sc
            result.content[0].text = json.dumps(sc)
            return result

        # 其他情况统一回退为默认打包（即使 text 为空，也与原逻辑在有 schema 分支一致）
        result.structured_content = pack(text)
        result.content[0].text = json.dumps(result.structured_content)
        return result


def _create_dynamic_config_model(
    plugin_name: str,
    config_schema: list[PluginConfigSchema],
) -> type[BaseModel]:
    """
    根据插件清单中的 config_schema 动态创建一个 Pydantic 模型。
    """
    field_definitions: dict[str, Any] = {}

    # Python 类型映射
    type_map = {
        "string": str,
        "number": float,
        "integer": int,  # 建议在 PluginConfigSchema 中也添加 "integer"
        "boolean": bool,  # 建议在 PluginConfigSchema 中也添加 "boolean"
    }

    for item in config_schema:
        field_name = item.name

        # 决定字段类型
        field_type = type_map.get(item.type, str)  # 默认为 string

        # 处理 secret 字段，使用 Pydantic 的 SecretStr 类型
        if getattr(item, "secret", False):  # 假设你的 PluginConfigSchema 有 secret 字段
            field_type = SecretStr

        # 构建 Field Info
        if item.required:
            # 必需字段
            field_info = Field(..., description=item.description)
        else:
            # 可选字段，带默认值
            field_info = Field(default=item.default, description=item.description)

        field_definitions[field_name] = (field_type, field_info)

    # 使用 pydantic.create_model 创建模型类
    DynamicConfigModel = create_model(
        f"{plugin_name.capitalize()}ConfigModel",
        **field_definitions,
    )
    return DynamicConfigModel


def _prepare_environment(validated_config: BaseModel) -> dict[str, str]:
    """
    将验证后的 Pydantic 配置模型实例转换为环境变量字典。
    """
    env_vars = {}
    for field_name, value in validated_config.model_dump().items():
        if value is None:
            continue

        # 如果是 SecretStr，则获取其真实值
        if isinstance(getattr(validated_config, field_name), SecretStr):
            secret_value = getattr(validated_config, field_name).get_secret_value()
            env_vars[field_name] = secret_value
        else:
            # 环境变量必须是字符串
            env_vars[field_name] = str(value)

    return env_vars


middleware = ResourceMiddleware()


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
    ) -> "PluginInstance":
        """
        异步工厂方法：创建并完全初始化一个插件实例。
        """
        if not user_config.enabled:
            raise ValueError(f"Plugin '{manifest.name}' is not enabled. This should not happend")
        env = {}
        validated_config_dict = {}

        # 1. 验证和处理用户配置
        if manifest.config_schema:
            # 1.1 动态创建 Pydantic 模型
            DynamicConfigModel = _create_dynamic_config_model(manifest.name, manifest.config_schema)

            try:
                # 1.2 使用动态模型验证用户提供的配置
                # 我们假设 user_config.config 是一个字典，如 {"DAPPIER_API_KEY": "..."}
                validated_model = DynamicConfigModel.model_validate(user_config.config or {})

                # 1.3 将验证后的配置转换为字典和环境变量
                validated_config_dict = validated_model.model_dump(mode="json")  # 保存验证后的配置
                env = _prepare_environment(validated_model)

            except ValidationError as e:
                logger.error(f"Validation error for plugin '{manifest.name}': {e}")

        # 1. 执行原有的同步初始化逻辑来创建 mcp_client
        if manifest.execution.mode == "remote":
            assert manifest.execution.url is not None
            if manifest.execution.url.endswith("sse"):
                transport = SSETransport(url=manifest.execution.url, headers=env)
            else:
                transport = StreamableHttpTransport(url=manifest.execution.url, headers=env, auth="oauth")

            # async with Client(transport) as client:
            #     await client.ping()

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
            log_with_context(
                "error",
                "Failed to connect to MCP server: {error_msg}",
                context={"plugin": manifest.name, "error_msg": f"{e}"},
            )

        mcp = FastMCP(name=user_config.name)
        mcp.mount(remote_proxy)
        mcp.add_middleware(middleware)

        base_tools_dict = await mcp.get_tools()

        # handler tools enabled status
        if not user_config.tools_default_enabled:
            for tool in base_tools_dict.values():
                mirrored_tool = tool.copy()
                mirrored_tool.disable()
                mcp.add_tool(mirrored_tool)

        for tool in user_config.tools or []:
            base_tool = base_tools_dict.get(tool.name)
            if not base_tool:
                continue
            logger.info(f"Translating tool {tool.name} to user config")
            trans_tool = Tool.from_tool(base_tool, name=tool.name, description=tool.description, enabled=tool.enabled)
            mcp.add_tool(trans_tool)
            # If the tool's name changed, we should add a new diabled tool to override original tool
            if tool.name != base_tool.name:
                mirrored_tool = base_tool.copy()
                mirrored_tool.disable()
                mcp.add_tool(mirrored_tool)
            # base_tool.disable()
        mcp_client = Client(mcp)

        instance = cls(name=user_config.name, mcp_client=mcp_client, mcp=mcp, status=_status, config=validated_config_dict, manifest=manifest, transport=transport)

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
        """
        Merges the plugin's config schema with the user's current values.

        Returns a list of details perfect for UI rendering.
        """
        if not self.manifest or not self.manifest.config_schema:
            return []

        details = []
        for schema_item in self.manifest.config_schema:
            current_value = (self.config or {}).get(schema_item.name)

            # For secrets, we should not expose the actual value.
            # We can return a placeholder or just indicate that it's set.
            # Here, we return a placeholder if the value is set.
            is_secret = getattr(schema_item, "secret", False)
            if is_secret and current_value is not None:
                display_value = "********"  # Placeholder for secrets
            else:
                display_value = current_value

            item_detail = ConfigItemDetail(
                name=schema_item.name,
                type=schema_item.type,
                description=schema_item.description,
                required=schema_item.required,
                secret=is_secret,
                default=schema_item.default,
                value=display_value,  # Use the placeholder-aware value
            )
            details.append(item_detail)

        return details


class PluginManifest(BaseModel):
    """ """

    name: str = Field(..., description="插件的唯一标识符")
    version: str | float = Field("0.2.0", description="插件版本 (遵循语义化版本)")
    spec_version: str | float = Field("2.0", description="插件规范版本 (遵循语义化版本)")
    description: str
    execution: ExecutionModel
    dependencies: list[str] | None = None
    python_version: str | None = None
    config_schema: list[PluginConfigSchema] | None = None
    _plugin_path: Path | None = PrivateAttr(default=None)

    @property
    def path(self) -> Path:
        if self._plugin_path is None:
            raise AttributeError("Plugin path has not been set.")
        return self._plugin_path

    @classmethod
    def from_toml(cls, toml_path: Path) -> "PluginManifest":
        """
        Loads a plugin manifest from a toml file, using pyproject.toml as a base
        if it exists, and giving priority to plugin.toml for any overlapping fields.
        """
        if not toml_path.is_file():
            raise FileNotFoundError(f"'plugin.toml' not found at '{toml_path}'")

        plugin_dir = toml_path.parent
        pyproject_toml_path = plugin_dir / "pyproject.toml"

        # 1. Initialize with data from pyproject.toml if it exists
        base_meta = {}
        if pyproject_toml_path.is_file():
            pyproject_data = toml.load(pyproject_toml_path)
            # We use the standard [project] table from PEP 621
            project_section = pyproject_data.get("project", {})
            # We only take the keys that are relevant to PluginManifest
            valid_keys = cls.model_fields.keys()
            base_meta = {k: v for k, v in project_section.items() if k in valid_keys}

        # 2. Load the specific plugin.toml data
        plugin_info = toml.load(toml_path)
        plugin_meta = plugin_info.get("plugin", {})

        # 3. Merge the two dictionaries.
        #    Keys in plugin_meta will overwrite keys in base_meta.
        final_meta = base_meta | plugin_meta

        # 4. Create the manifest instance
        manifest = cls(**final_meta)
        manifest._plugin_path = plugin_dir
        return manifest

    async def create_instance(
        self,
        user_config: PluginUserConfig,
    ) -> "PluginInstance":
        """
        工厂方法：使用用户配置来创建一个运行时实例。
        """
        if self.path is None:
            raise ValueError("Plugin path is not set. Please set the path before creating an instance.")
        return await PluginInstance.from_config(
            manifest=self,
            user_config=user_config,
        )


class PluginManager:
    plugins: dict[str, PluginManifest] = {}

    def __init__(self, plugin_dir: str | None = None):
        if not plugin_dir:
            project_root = find_project_root()
            if project_root:
                self.plugin_dir = project_root / "backend" / "plugins"
            else:
                raise ValueError("Plugin directory must be specified or a project root must be found.")
        else:
            self.plugin_dir = Path(plugin_dir)
        if self.plugin_dir:
            logger.info(f"Initializing PluginManager, scanning directory: '{self.plugin_dir}'")
            self._scan_and_register_plugins()

    def _scan_and_register_plugins(self):
        if not self.plugin_dir.is_dir():
            logger.warning(f"Warning: Plugin directory '{self.plugin_dir}' not found.")
            return

        for plugin_path in self.plugin_dir.iterdir():
            if not plugin_path.is_dir():
                logger.warning(f"Skipping '{plugin_path}' as it is not a directory.")
                continue

            toml_path = plugin_path / "plugin.toml"
            if not toml_path.is_file():
                logger.warning(f"Skipping '{plugin_path}' as 'plugin.toml' is missing.")
                continue
            try:
                plugin_manifest = PluginManifest.from_toml(toml_path)
                self.plugins[plugin_manifest.name] = plugin_manifest
            except Exception as e:
                logger.error(f"Error loading plugin from '{plugin_path}': {e}")

    def list_plugins(self) -> dict[str, PluginManifest]:
        return self.plugins

    async def create_instance(self, instance_settings: PluginUserConfig):
        plugin_name = instance_settings.plugin_name
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin '{plugin_name}' is not registered or failed to load.")
        plugin_definition = self.plugins[plugin_name]
        return await plugin_definition.create_instance(instance_settings)

    def get_plugin_manifest(self, plugin_name: str) -> PluginManifest | None:
        """
        获取指定插件的 Manifest。
        """
        return self.plugins.get(plugin_name)

    def remove_plugin(self, plugin_name):
        if plugin_name in self.plugins:
            logger.error(f"Plugin '{self.plugins[plugin_name].path}' removed from PluginManager.")
        else:
            logger.warning(f"Plugin '{plugin_name}' not found in PluginManager.")


plugin_manager = None


def get_plugin_manager() -> PluginManager:
    global plugin_manager
    if plugin_manager is None:
        plugin_manager = PluginManager()
    return plugin_manager
