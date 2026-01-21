from pydantic import BaseModel
from typing import List, Optional


# Level 3 (Deepest)
class Detail(BaseModel):
    info: str
    tags: List[str]


# Level 2
class Item(BaseModel):
    name: str
    detail: Detail

    # 模拟可能导致问题的普通类（非 Pydantic Model）
    class Config:
        arbitrary_types_allowed = True


class NonPydanticClass:
    def __init__(self, value):
        self.value = value


# Level 1 (Root)
class RootModel(BaseModel):
    id: int
    items: List[Item]
    # 尝试嵌套一个可能无法序列化的字段
    # custom_obj: Optional[NonPydanticClass] = None


# Create instances
detail = Detail(info="deep info", tags=["a", "b"])
item = Item(name="item1", detail=detail)
root = RootModel(id=1, items=[item])

# Dump
print(root.model_dump_json(indent=2))
