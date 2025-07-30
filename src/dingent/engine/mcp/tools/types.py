from typing import TypeVar

from pydantic import BaseModel

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


# ToolOutput = Union[List[PydanticModel], pd.DataFrame]
class ToolOutput(BaseModel):
    """Pydantic模型基类，所有资源的数据模型都应继承自它，用于数据校验。"""

    type: str

    payload: dict

    metadata: dict = {}
