from typing import TypeVar

from pydantic import BaseModel

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class TablePayload(BaseModel):
    columns: list[str]
    rows: list[dict]
    title: str = ""


class ToolOutput(BaseModel):
    type: str

    payload: TablePayload

    metadata: dict = {}
