from typing import Literal

from pydantic import BaseModel


class User(BaseModel):
    username: str
    id: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None
    role: Literal["admin", "user", "guest"] = "user"
