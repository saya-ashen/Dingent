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


class BaseSettings(BaseModel):
    name: str = Field(description="The unique name of the tool instance")
    description: str = Field()
