import toml
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID
from pydantic import Field, PrivateAttr
from dingent.core.types import ExecutionModel


import re
from typing import Any
from pydantic import BaseModel, Field
from sqlmodel import SQLModel


def generate_id_from_name(display_name: str) -> str:
    """根据显示名称生成一个唯一的、机器友好的ID (Slugify)"""
    s = display_name.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s


class AssistantBase(SQLModel):
    name: str = Field(..., description="The display name of the assistant.")
    description: str
    version: str | float = Field("0.2.0", description="Assistant version.")
    spec_version: str | float = Field("2.0", description="Specification version.")
    enabled: bool = Field(True, description="Enable or disable the assistant.")


class PluginBase(BaseModel):
    id: str = Field(..., description="插件的唯一永久ID")

    display_name: str = Field(..., description="插件的显示名称")
    description: str = Field(..., description="插件描述")
    version: str | float = Field("0.1.0", description="插件版本")


class PluginManifest(PluginBase):
    """
    Acts as the static definition or blueprint of a plugin.
    Its sole source of truth is the plugin.toml file created by the plugin developer
    """

    id: str = Field(default="no_name_plugin", description="插件唯一标识符")
    spec_version: str | float = Field("2.0", description="插件规范版本 (遵循语义化版本)")
    execution: ExecutionModel
    dependencies: list[str] | None = None
    python_version: str | None = None
    config_schema: list["PluginConfigSchema"] | None = None
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


class ToolOverrideConfig(BaseModel):
    name: str
    enabled: bool = True
    description: str | None = None


class PluginRead(PluginBase):
    enabled: bool = True
    tools: list[ToolOverrideConfig] | None = None
    config: dict | None = None
    status: str


class AssistantRead(AssistantBase):
    id: str = Field(..., description="The unique and permanent ID for the assistant.")
    status: str = Field(..., description="运行状态 (active/inactive/error)")
    plugins: list[PluginRead]


class AssistantCreate(AssistantBase):
    pass


class AssistantUpdate(AssistantBase):
    plugins: list[PluginRead] | None = None


class PluginAddRequest(BaseModel):
    """
    Schema for the request body when adding a plugin to an assistant.
    """

    plugin_id: UUID


class PluginUpdateRequest(BaseModel):
    """
    Schema for updating a plugin's configuration within an assistant.
    All fields are optional for PATCH functionality.
    """

    enabled: Optional[bool] = None
    tools_default_enabled: Optional[bool] = None
    tools_override: Optional[list[dict[str, Any]]] = None
    user_config_values: Optional[dict[str, Any]] = None


class PluginConfigSchema(BaseModel):
    name: str = Field(..., description="配置项的名称 (环境变量名)")
    type: Literal["string", "float", "integer", "bool"] = Field(..., description="配置项的期望类型 (e.g., 'string', 'number')")
    required: bool = Field(..., description="是否为必需项")
    secret: bool = Field(False, description="是否为敏感信息 (如 API Key)")
    description: str | None = Field(None, description="该配置项的描述")
    default: Any | None = Field(None, description="默认值 (如果存在)")


class ConfigItemDetail(PluginConfigSchema):
    """Represents a single configuration item with its schema and value."""

    value: Any | None = Field(None, description="用户设置的当前值")
