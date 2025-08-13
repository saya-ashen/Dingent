from typing import Literal

from pydantic import (
    BaseModel,
)


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
