from typing import Any
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict[str, Any]  # 返回一些用户信息给前端
