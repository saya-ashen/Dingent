from typing import Any, TypeVar

from pydantic import BaseModel
from sqlmodel import MetaData
from sqlmodel import SQLModel as SQLModelBase

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class TablePayload(BaseModel):
    columns: list[str]
    rows: list[dict]
    title: dict = {}

class ToolOutput(BaseModel):
    """Pydantic模型基类，所有资源的数据模型都应继承自它，用于数据校验。"""

    type: str

    payload: TablePayload

    metadata: dict = {}


def make_sqlmodel_base(name:str):
    """
    工厂函数：创建一个新的、独立的 SQLModel 上下文。
    """
    class SQLModel(SQLModelBase):
        model_config = {
            "extra": "allow"
        }
        def model_dump(self, *args, **kwargs) -> dict[str, Any]:
            model_dump = super().model_dump(*args, **kwargs)

            if kwargs.get("by_alias") is False:
                return model_dump

            for field_name, field_info in self.__fields__.items():
                if field_info.alias and field_name in model_dump:
                    model_dump[field_info.alias] = model_dump.pop(field_name)

            return model_dump
        metadata = MetaData(schema=name)

    return SQLModel
