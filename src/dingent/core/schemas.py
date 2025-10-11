from mcp.types import Tool
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict
import toml
from pathlib import Path
from typing import Callable, Literal, Optional
from uuid import UUID
from pydantic import ConfigDict, PrivateAttr
from dingent.core.types import ExecutionModel


import re
from typing import Any
from sqlmodel import SQLModel, Field

from dingent.core.utils import to_camel


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


class PluginBase(SQLModel):
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


class ToolOverrideConfig(SQLModel):
    name: str
    enabled: bool = True
    description: str | None = None


class PluginRead(PluginBase):
    id: UUID = Field(..., description="插件的唯一永久ID")
    enabled: bool = True
    tools: list[ToolOverrideConfig] | None = None
    config: dict | None = None
    status: str | None = Field(None, description="运行状态 (active/inactive/error)")


class PluginCreate(PluginBase):
    spec_version: str | float = Field("2.0", description="插件规范版本 (遵循语义化版本)")


class AssistantRead(AssistantBase):
    id: str = Field(..., description="The unique and permanent ID for the assistant.")
    status: str = Field(..., description="运行状态 (active/inactive/error)")
    plugins: list[PluginRead]


class AssistantCreate(AssistantBase):
    pass


class AssistantUpdate(AssistantBase):
    plugins: list[PluginRead] | None = None


class PluginAddToAssistant(SQLModel):
    """
    Schema for the request body when adding a plugin to an assistant.
    """

    id: UUID


class PluginUpdateOnAssistant(SQLModel):
    """
    Schema for updating a plugin's configuration within an assistant.
    All fields are optional for PATCH functionality.
    """

    enabled: Optional[bool] = None
    tools_default_enabled: Optional[bool] = None
    tools_override: Optional[list[dict[str, Any]]] = None
    user_config_values: Optional[dict[str, Any]] = None


class PluginConfigSchema(SQLModel):
    name: str = Field(..., description="配置项的名称 (环境变量名)")
    type: Literal["string", "float", "integer", "bool"] = Field(..., description="配置项的期望类型 (e.g., 'string', 'number')")
    required: bool = Field(..., description="是否为必需项")
    secret: bool = Field(False, description="是否为敏感信息 (如 API Key)")
    description: str | None = Field(None, description="该配置项的描述")
    default: Any | None = Field(None, description="默认值 (如果存在)")


class ConfigItemDetail(PluginConfigSchema):
    """Represents a single configuration item with its schema and value."""

    value: Any | None = Field(None, description="用户设置的当前值")


class RunnableTool(SQLModel):
    tool: Tool
    run: Callable[[dict], Any]


class UserRead(SQLModel):
    id: str
    username: str
    email: str
    full_name: str | None = None
    role: list[str] = Field(default_factory=lambda: ["user"])


# ==============================================================================
# WorkflowNode Models
# ==============================================================================


class WorkflowNodeBase(SQLModel):
    """节点的基础共享字段"""

    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    assistant_id: UUID
    position: Dict[str, float]
    is_start_node: bool = False
    type: str = "assistant"


class WorkflowNodeCreate(WorkflowNodeBase):
    """
    用于创建节点。
    前端在 POST /workflows/{workflow_id}/nodes 时发送此模型。
    workflow_id 从 URL 中获取，不需要在 body 中提供。
    """

    measured: dict[str, float] = {}
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    is_start_node: bool = False
    type: str = "assistant"


class WorkflowNodeUpdate(SQLModel):
    """
    用于更新节点。
    前端在 PATCH /workflows/{workflow_id}/nodes/{node_id} 时发送此模型。
    通常只允许更新位置等 UI 相关属性。
    """

    position: Optional[Dict[str, float]] = None
    is_start_node: Optional[bool] = None


class WorkflowNodeRead(WorkflowNodeBase):
    """用于从 API 读取节点数据。"""

    id: UUID
    workflow_id: UUID


# ==============================================================================
# WorkflowEdge Models
# ==============================================================================


class WorkflowEdgeBase(SQLModel):
    """边的基础共享字段"""

    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    source: UUID
    target: UUID
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    type: str = "directrional"


class WorkflowEdgeCreate(WorkflowEdgeBase):
    """
    用于创建边。
    前端在 POST /workflows/{workflow_id}/edges 时发送此模型。
    """

    pass


class WorkflowEdgeUpdate(SQLModel):
    """
    用于更新边。
    通常边很少被更新，一般是删除后重建。但可以预留接口。
    """

    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    type: Optional[str] = None


class WorkflowEdgeRead(WorkflowEdgeBase):
    """用于从 API 读取边数据。"""

    id: UUID
    workflow_id: UUID


# ==============================================================================
# Workflow Models
# ==============================================================================


class WorkflowBase(SQLModel):
    """工作流的基础共享字段"""

    description: Optional[str] = None


class WorkflowCreate(WorkflowBase):
    """
    用于创建工作流。
    前端在 POST /workflows 时发送此模型。
    user_id 从认证信息中获取。
    """

    name: str

    pass


class WorkflowReplace(WorkflowBase):
    """
    用于替换整个工作流，包括其节点和边。
    前端在 PUT /workflows/{workflow_id} 时发送此模型。
    注意：这会覆盖现有的节点和边。
    """

    name: str
    nodes: List[WorkflowNodeCreate] = []
    edges: List[WorkflowEdgeCreate] = []


class WorkflowUpdate(WorkflowBase):
    """
    用于更新工作流元数据（名称、描述）。
    前端在 PATCH /workflows/{workflow_id} 时发送此模型。
    注意：节点的修改不在这里处理，而是通过专门的节点接口。
    """

    name: Optional[str] = None


class WorkflowReadBasic(WorkflowBase):
    """
    用于在列表中读取工作流的基础信息。
    不包含 nodes 和 edges，避免数据冗余。
    """

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class WorkflowRead(WorkflowReadBasic):
    """
    用于读取单个工作流的完整信息，包含其所有的节点和边。
    前端在 GET /workflows/{workflow_id} 时会收到此模型。
    """

    nodes: List[WorkflowNodeRead] = []
    edges: List[WorkflowEdgeRead] = []
