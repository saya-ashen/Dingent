from datetime import datetime
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from dingent.core.types import WorkspaceRole


class UserRead(SQLModel):
    id: UUID
    username: str
    email: str
    full_name: str | None = None
    role: list[str] = Field(default_factory=lambda: ["user"])


class UserCreate(SQLModel):
    username: str
    email: EmailStr
    password: str


class WorkspaceBase(SQLModel):
    name: str
    slug: str
    description: str | None = None
    allow_guest_access: bool = False


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    allow_guest_access: bool | None = None
    default_model_config_id: UUID | None = None


class WorkspaceMemberRead(SQLModel):
    user_id: UUID
    email: str
    username: str
    role: WorkspaceRole
    joined_at: datetime
    avatar_url: str | None = None


class WorkspaceRead(WorkspaceBase):
    id: UUID
    role: WorkspaceRole
    slug: str
    created_at: datetime
    default_model_config_id: UUID | None = None
    # 简单的成员概览
    member_count: int | None = None


class WorkspaceInvite(SQLModel):
    email: EmailStr
    role: WorkspaceRole


class WorkspaceWithRole(WorkspaceRead):
    pass
    # permissions: list[str] = [] # 可选：更细粒度的权限列表


class ThreadBase(SQLModel):
    id: str | UUID


class ThreadRead(ThreadBase):
    id: str | UUID
    title: str
    workspace_id: UUID
    user_id: UUID | None
    visitor_id: str | None
    created_at: datetime
    updated_at: datetime
