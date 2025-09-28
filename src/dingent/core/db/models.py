from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, Relationship, SQLModel


class ToolOverrideConfig(BaseModel):
    """
    定义存储在数据库 JSON 字段中的单个工具覆盖配置的结构。
    这不是一个数据库表模型。
    """

    name: str = Field(..., description="要配置的工具的唯一名称")
    enabled: bool = Field(True, description="此 Assistant 是否启用该工具")
    description: str | None = Field(None, description="可选的、为此 Assistant 定制的工具描述")
    # 未来可以扩展更多可覆盖的字段


# --- 用户与所有权模型 ---


class User(SQLModel, table=True):
    """
    用户模型，其他用户创建的资源都与此模型关联。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 关系
    assistants: List["Assistant"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    workflows: List["Workflow"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    resources: List["Resource"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# --- Assistant、Plugin 及其关联（多对多） ---


class AssistantPluginLink(SQLModel, table=True):
    """
    Assistant 与 Plugin 的多对多链接表；同时保存用户侧配置。
    """

    assistant_id: UUID = Field(foreign_key="assistant.id", primary_key=True)
    plugin_id: UUID = Field(foreign_key="plugin.id", primary_key=True)

    enabled: bool = True
    # tools_default_enabled: bool = True

    # --- 针对单个工具的覆盖配置 ---
    # 存储一个列表，每个元素都是一个符合 ToolOverrideConfig 结构的字典
    # 例如: [{"name": "get_weather", "enabled": false}, {"name": "send_email", "description": "Send email on behalf of the user"}]
    tool_configs: List[ToolOverrideConfig] = Field(default=None, sa_column=Column(JSON), description="用户对该插件下特定工具的覆盖配置列表")

    # --- 用户为插件提供的配置值 (如 API Keys) ---
    user_config_values: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # 双向关系（注意 back_populates 名称需与目标模型中的属性名对应）
    assistant: "Assistant" = Relationship(back_populates="plugin_links")
    plugin: "Plugin" = Relationship(back_populates="assistant_links")


class Assistant(SQLModel, table=True):
    """
    Assistant 模型：属于某个用户；可关联多个 Plugin（多对多）。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str
    description: Optional[str] = None
    version: str = "0.2.0"
    spec_version: str = "3.0"
    enabled: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # 外键：多对一 -> User
    user_id: UUID = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="assistants")

    # 多对多：通过 link_model
    plugins: List["Plugin"] = Relationship(
        back_populates="assistants",
        link_model=AssistantPluginLink,
    )

    # 提供对链接记录本身的直达访问（便于读写 per-assistant 配置）
    plugin_links: List[AssistantPluginLink] = Relationship(back_populates="assistant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    # 一个 Assistant 可被多个 WorkflowNode 引用
    workflow_nodes: List["WorkflowNode"] = Relationship(back_populates="assistant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class Plugin(SQLModel, table=True):
    """
    插件的全局定义：系统级资源；用户侧配置在 AssistantPluginLink 中。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    plugin_slug: str = Field(unique=True, index=True)
    name: str
    description: str
    version: str = "0.1.0"

    config_schema: Optional[List[dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

    # 多对多
    assistants: List["Assistant"] = Relationship(
        back_populates="plugins",
        link_model=AssistantPluginLink,
    )

    # 反向访问链接表
    assistant_links: List[AssistantPluginLink] = Relationship(back_populates="plugin", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# --- Workflow 及其结构 ---


class Workflow(SQLModel, table=True):
    """
    Workflow：属于某个用户，包含节点与边。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str
    description: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # 外键：多对一 -> User
    user_id: UUID = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="workflows")

    # 关系
    nodes: List["WorkflowNode"] = Relationship(back_populates="workflow", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    edges: List["WorkflowEdge"] = Relationship(back_populates="workflow", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class WorkflowNode(SQLModel, table=True):
    """
    Workflow 中的节点：引用一个 Assistant。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    assistant_id: UUID = Field(foreign_key="assistant.id", index=True)

    # UI 相关
    type: str = "assistant"
    is_start_node: bool = Field(default=False, index=True)
    position: dict[str, float] = Field(sa_column=Column(JSON))

    # 关系：多对一 -> Workflow；多对一 -> Assistant
    workflow: Workflow = Relationship(back_populates="nodes")
    assistant: Assistant = Relationship(back_populates="workflow_nodes")


class WorkflowEdge(SQLModel, table=True):
    """
    Workflow 中的边：连接两个 WorkflowNode。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)

    source_node_id: UUID = Field(foreign_key="workflownode.id", index=True)
    target_node_id: UUID = Field(foreign_key="workflownode.id", index=True)

    # UI 相关
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    type: str = "default"
    mode: str = "single"

    workflow: Workflow = Relationship(back_populates="edges")


# --- 运行时数据模型 ---


class Resource(SQLModel, table=True):
    """
    存储工具结果的资源。属于某个用户。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    version: str = "1.0"
    model_text: str = Field(sa_column=Column(Text))

    display: Optional[List[dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    data: dict | str | list | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # 所有权：多对一 -> User
    user_id: UUID = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="resources")
