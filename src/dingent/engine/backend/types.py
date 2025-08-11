from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from dingent.engine.plugins.types import BasePluginSettings


class AssistantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DING_")

    name: str = Field(..., description="")
    description: str
    tools: list[BasePluginSettings] = []
    version: str | float = Field("0.2.0", description="")
    spec_version: str | float = Field("2.0", description="")


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
