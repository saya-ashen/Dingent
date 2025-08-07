from typing import TypeVar

from pydantic import BaseModel, Field

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class TablePayload(BaseModel):
    columns: list[str]
    rows: list[dict]
    title: str = ""


class ToolOutput(BaseModel):
    type: str

    payload: TablePayload

    metadata: dict = {}


class ToolBaseSettings(BaseModel):
    model_config = {"extra": "allow"}

    type: str = Field(description="The type name of the tool, e.g., 'text2sql'")
    name: str = Field(description="The unique name of the tool instance")
    enabled: bool = True
    description: str = Field()
    exclude_args: list[str] = []
