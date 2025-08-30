from typing import Any

from pydantic import BaseModel, Field

from dingent.core.types import (
    AssistantBase,
    AssistantCreate,
    AssistantUpdate,
    ConfigItemDetail,
    PluginUserConfig,
)

# --- Admin Response Models ---


class ToolAdminDetail(BaseModel):
    name: str
    description: str
    enabled: bool


class PluginAdminDetail(PluginUserConfig):
    name: str = Field(..., description="插件名称")
    tools: list[ToolAdminDetail] = Field(default_factory=list, description="该插件的工具列表")
    status: str = Field(..., description="运行状态 (active/inactive/error)")
    config: list[ConfigItemDetail] = Field(default_factory=list)


class AssistantAdminDetail(AssistantBase):
    id: str
    status: str = Field(..., description="运行状态 (active/inactive/error)")
    plugins: list[PluginAdminDetail]


class AppAdminDetail(BaseModel):
    current_workflow: str | None = None
    workflows: list[dict[str, str]] = Field(default_factory=list)
    llm: dict[str, Any]


# --- Request Models ---


class AddPluginRequest(BaseModel):
    plugin_id: str
    config: dict[str, Any] | None = None
    enabled: bool = True
    tools_default_enabled: bool = True


class UpdatePluginConfigRequest(BaseModel):
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    tools_default_enabled: bool | None = None
    tools: list[str] | None = None


class ReplacePluginsRequest(BaseModel):
    plugins: list[PluginUserConfig]


class AssistantsBulkReplaceRequest(BaseModel):
    assistants: list[AssistantCreate | AssistantUpdate | dict]


class AssistantCreateRequest(AssistantCreate):
    pass


class AssistantUpdateRequest(AssistantUpdate):
    pass


class SetActiveWorkflowRequest(BaseModel):
    workflow_id: str


class MarketDownloadRequest(BaseModel):
    item_id: str
    category: str  # "plugin" | "assistant" | "workflow"


class MarketDownloadResponse(BaseModel):
    success: bool
    message: str
    installed_path: str | None = None
