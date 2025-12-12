from typing import Any
import uuid

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


class AgentExecuteRequest(BaseModel):
    threadId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: dict[str, Any] = {}
    messages: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    nodeName: str | None = None
    config: dict[str, Any] | None = None
    metaEvents: list[dict[str, Any]] = []


class ActionExecuteRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


class AgentStateRequest(BaseModel):
    threadId: str
