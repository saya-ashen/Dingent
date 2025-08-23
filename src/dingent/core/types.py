from typing import Any, Literal, TypeVar

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    model_validator,
)

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class ConfigItemDetail(BaseModel):
    """Represents a single configuration item with its schema and value."""

    name: str = Field(..., description="配置项的名称 (环境变量名)")
    type: str = Field(..., description="配置项的期望类型 (e.g., 'string', 'number')")
    required: bool = Field(..., description="是否为必需项")
    secret: bool = Field(False, description="是否为敏感信息 (如 API Key)")
    description: str | None = Field(None, description="该配置项的描述")
    default: Any | None = Field(None, description="默认值 (如果存在)")
    value: Any | None = Field(None, description="用户设置的当前值")


class PluginConfigSchema(BaseModel):
    name: str
    type: Literal["string", "float", "integer", "bool"]
    required: bool = True
    secret: bool = False
    default: str | int | float | None = None
    description: str | None = None


class ToolOverrideConfig(BaseModel):
    name: str
    enabled: bool = True
    description: str | None = None


class PluginUserConfig(BaseModel):
    """
    Developer should inherit this class to define user-specific plugin configuration.
    """

    name: str
    plugin_name: str
    tools_default_enabled: bool = True
    enabled: bool = True
    tools: list[ToolOverrideConfig] | None = None
    config: dict | None = None


class ExecutionModel(BaseModel):
    """定义插件的运行方式"""

    mode: Literal["local", "remote"] = Field(..., description="运行模式: 'local' 或 'remote'")

    url: str | None = None
    script_path: str | None = Field(None, description="插件管理器需要运行的Python入口文件路径")
    mcp_json_path: str | None = None

    @model_validator(mode="after")
    def check_exclusive_execution_mode(self) -> "ExecutionModel":
        """校验器：确保 'local' 和 'remote' 配置与 'mode' 字段匹配"""
        return self


class ToolConfigModel(BaseModel):
    """用户个性化配置的定义"""

    schema_path: FilePath = Field(..., description="指向一个包含用户配置Pydantic类的Python文件")


class TablePayload(BaseModel):
    type: Literal["table"] = "table"
    columns: list[str]
    rows: list[dict]
    title: str = ""


class MarkdownPayload(BaseModel):
    type: Literal["markdown"] = "markdown"
    content: str


class ToolOutput(BaseModel):
    payloads: list[TablePayload | MarkdownPayload]

    metadata: dict = {}


class AssistantBase(BaseModel):
    name: str = Field(..., description="The name of the assistant.")
    description: str
    version: str | float = Field("0.2.0", description="Assistant version.")
    spec_version: str | float = Field("2.0", description="Specification version.")
    enabled: bool = Field(True, description="Enable or disable the assistant.")


class AssistantCreate(AssistantBase):
    pass


class AssistantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    plugins: list[PluginUserConfig] | None = None
    version: str | float | None = None
    spec_version: str | float | None = None
    enabled: bool | None = None


class PluginBase(BaseModel):
    name: str = Field(..., description="插件名称")
    description: str = Field(..., description="插件描述")
    version: str | float = Field("0.1.0", description="插件版本")


class WorkflowNodeData(BaseModel):
    assistantId: str = Field(..., description="Assistant ID referenced by this node")
    assistantName: str = Field(..., description="Assistant name for display")
    description: str | None = Field(None, description="Node description")


class WorkflowNode(BaseModel):
    id: str = Field(..., description="Unique node identifier")
    type: Literal["assistant", "start"] = Field("assistant", description="Node type")
    position: dict[str, float] = Field(..., description="Node position {x, y}")
    data: WorkflowNodeData = Field(..., description="Node data")


class WorkflowEdgeData(BaseModel):
    condition: str | None = Field(None, description="Edge condition")
    label: str | None = Field(None, description="Edge label")


class WorkflowEdge(BaseModel):
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str | None = Field("default", description="Edge type")
    data: WorkflowEdgeData | None = Field(None, description="Edge data")


class WorkflowBase(BaseModel):
    name: str = Field(..., description="Workflow name")
    description: str | None = Field(None, description="Workflow description")


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None


class Workflow(WorkflowBase):
    id: str = Field(..., description="Unique workflow identifier")
    nodes: list[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="Workflow edges")
    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")
