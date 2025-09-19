from typing import Any
from typing import List
from pydantic import BaseModel, EmailStr
from pydantic import BaseModel


class UserPublic(BaseModel):
    username: str
    id: str
    email: EmailStr
    full_name: str | None = None
    role: List[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
