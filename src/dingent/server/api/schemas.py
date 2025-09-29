from typing import Any

from pydantic import BaseModel, Field


# --- Admin Response Models ---


class ToolAdminDetail(BaseModel):
    name: str
    description: str
    enabled: bool


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


class SetActiveWorkflowRequest(BaseModel):
    workflow_id: str


class MarketDownloadRequest(BaseModel):
    item_id: str
    category: str  # "plugin" | "assistant" | "workflow"


class MarketDownloadResponse(BaseModel):
    success: bool
    message: str
    installed_path: str | None = None
