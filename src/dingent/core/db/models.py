from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from openai import conversations
from pydantic import BaseModel
from pydantic import Field as PydField
from sqlalchemy import JSON, Column, LargeBinary, Text
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from dingent.core.schemas import AssistantSpec, NodeSpec, PluginSpec, WorkflowSpec


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"
    ADMIN = "admin"
    GUEST = "guest"


class ToolOverrideConfig(BaseModel):
    """
    定义存储在数据库 JSON 字段中的单个工具覆盖配置的结构。
    这不是一个数据库表模型。
    """

    name: str = PydField(..., description="要配置的工具的唯一名称")
    enabled: bool = PydField(True, description="此 Assistant 是否启用该工具")
    description: str | None = PydField(None, description="可选的、为此 Assistant 定制的工具描述")
    # 未来可以扩展更多可覆盖的字段


# --- 用户与所有权模型 ---


class UserRoleLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role_id: int = Field(foreign_key="role.id", primary_key=True)


class Role(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # 例如 "admin", "user"
    description: str | None = None

    users: list["User"] = Relationship(back_populates="roles", link_model=UserRoleLink)


class WorkspaceMember(SQLModel, table=True):
    """
    用户与工作空间的多对多关联，包含用户在这个空间的角色（如管理员、普通成员）
    """

    workspace_id: UUID = Field(default_factory=uuid4, foreign_key="workspace.id", primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)

    role: WorkspaceRole = Field(default="member")
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    """
    用户模型：系统中的账户主体，所有用户资源都与此模型关联。
    """

    # 基本标识
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    username: str = Field(description="用户昵称，非唯一标识")
    email: str = Field(unique=True, index=True, description="用户邮箱（主要用于登录和通知）")
    roles: list[Role] = Relationship(back_populates="users", link_model=UserRoleLink)
    hashed_password: str
    encrypted_dek: bytes | None = Field(default=None, sa_column=Column(LargeBinary))

    # 用户状态
    is_active: bool = Field(default=True, description="账户是否激活")

    # 个人信息
    full_name: str | None = Field(default=None, description="真实姓名或昵称")
    avatar_url: str | None = Field(default=None, description="头像地址")

    # 审计字段
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    provider_credentials: list["UserProviderCredential"] = Relationship(back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"

    # 关系
    resources: list["Resource"] = Relationship(back_populates="created_by", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    workspaces: list["Workspace"] = Relationship(back_populates="members", link_model=WorkspaceMember)


class Workspace(SQLModel, table=True):
    """
    工作空间/团队：资源（Assistant/Workflow）的真正持有者
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(index=True, description="工作空间的显示名称")
    slug: str = Field(index=True, description="工作空间的唯一标识符，用于 URL 等")
    avatar_url: str | None = Field(default=None, description="工作空间的头像地址")
    description: str | None = None

    members: list["User"] = Relationship(back_populates="workspaces", link_model=WorkspaceMember)

    assistants: list["Assistant"] = Relationship(back_populates="workspace", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    workflows: list["Workflow"] = Relationship(back_populates="workspace")
    resources: list["Resource"] = Relationship(back_populates="workspace", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    conversations: list["Conversation"] = Relationship(back_populates="workspace", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Assistant、Plugin 及其关联（多对多） ---


class AssistantPluginLink(SQLModel, table=True):
    """
    Assistant 与 Plugin 的多对多链接表；同时保存用户侧配置。
    """

    assistant_id: UUID = Field(
        foreign_key="assistant.id",
        primary_key=True,
        index=True,
    )
    plugin_id: UUID = Field(
        foreign_key="plugin.id",
        primary_key=True,
        index=True,
    )

    enabled: bool = True

    # --- 针对单个工具的覆盖配置 ---
    # 存储一个列表，每个元素都是一个符合 ToolOverrideConfig 结构的字典
    # 例如: [{"name": "get_weather", "enabled": false}, {"name": "send_email", "description": "Send email on behalf of the user"}]
    tool_configs: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(MutableList.as_mutable(JSON)),
    )

    # --- 用户为插件提供的配置值 (如 API Keys) ---
    user_plugin_config: dict[str, Any] | None = Field(
        default_factory=dict,
        sa_column=Column(MutableDict.as_mutable(JSON)),
    )

    # 双向关系（注意 back_populates 名称需与目标模型中的属性名对应）
    assistant: "Assistant" = Relationship(back_populates="plugin_links")
    plugin: "Plugin" = Relationship(back_populates="assistant_links")


class Assistant(SQLModel, table=True):
    """
    Assistant 模型：属于某个用户；可关联多个 Plugin（多对多）。
    """

    __table_args__ = (UniqueConstraint("workspace_id", "name", name="unique_workspace_assistant_name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(index=True)
    description: str | None = None
    version: str = "0.2.0"
    spec_version: str = "3.0"
    enabled: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # 外键：多对一 -> User
    created_by_id: UUID | None = Field(default=None, foreign_key="user.id")
    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)  # <-- 新增这行
    workspace: Workspace = Relationship(back_populates="assistants")

    # 多对多：通过 link_model
    plugins: list["Plugin"] = Relationship(
        back_populates="assistants",
        link_model=AssistantPluginLink,
        sa_relationship_kwargs={"overlaps": "assistant,plugin_links"},
    )

    # 提供对链接记录本身的直达访问（便于读写 per-assistant 配置）
    plugin_links: list[AssistantPluginLink] = Relationship(back_populates="assistant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    # 一个 Assistant 可被多个 WorkflowNode 引用
    workflow_nodes: list["WorkflowNode"] = Relationship(back_populates="assistant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class Plugin(SQLModel, table=True):
    """
    插件的全局定义：系统级资源；用户侧配置在 AssistantPluginLink 中。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    registry_id: str = Field(..., unique=True, index=True)  # 标识插件来源的 ID，如 LOCAL、或某个市场的 ID
    registry_name: str = "Local"
    display_name: str
    description: str
    version: str = "0.1.0"

    config_schema: dict[str, Any] = Field(default=None, sa_column=Column(JSON))

    # 多对多
    assistants: list["Assistant"] = Relationship(
        back_populates="plugins",
        link_model=AssistantPluginLink,
    )

    # 反向访问链接表
    assistant_links: list[AssistantPluginLink] = Relationship(back_populates="plugin", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# --- Workflow 及其结构 ---


class Workflow(SQLModel, table=True):
    """
    Workflow：属于某个用户，包含节点与边。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str
    description: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # 外键：多对一 -> User
    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)
    workspace: Workspace = Relationship(back_populates="workflows")
    created_by_id: UUID | None = Field(default=None, foreign_key="user.id")

    # 关系
    nodes: list["WorkflowNode"] = Relationship(back_populates="workflow", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    edges: list["WorkflowEdge"] = Relationship(back_populates="workflow", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    def to_spec(self) -> WorkflowSpec:
        """将数据库实体转化为纯业务 Spec"""
        start_node = None
        for n in self.nodes:
            if n.is_start_node:
                start_node = n

        return WorkflowSpec(
            id=self.id,
            name=self.name,
            start_node_name=start_node.name if start_node else None,
            nodes=[
                NodeSpec(
                    id=n.id,
                    is_start_node=n.is_start_node,
                    assistant=AssistantSpec(
                        id=n.assistant.id,
                        name=n.assistant.name,
                        version=n.assistant.version,
                        description=n.assistant.description or "",
                        spec_version=n.assistant.spec_version,
                        enabled=n.assistant.enabled,
                        plugins=[
                            PluginSpec(
                                plugin_id=l.plugin.registry_id,
                                registry_id=l.plugin.registry_id,
                                config=l.user_plugin_config or {},
                            )
                            for l in n.assistant.plugin_links
                            if l.enabled
                        ],
                    ),
                )
                for n in self.nodes
            ],
        )


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
    position: dict[str, float] = Field(sa_column=Column(MutableDict.as_mutable(JSON)))
    measured: dict[str, float] = Field(default_factory=dict, sa_column=Column(MutableDict.as_mutable(JSON)))
    # 关系：多对一 -> Workflow；多对一 -> Assistant
    workflow: Workflow = Relationship(back_populates="nodes")
    assistant: Assistant = Relationship(back_populates="workflow_nodes")

    @property
    def name(self) -> str:
        return self.assistant.name


class WorkflowEdge(SQLModel, table=True):
    """
    Workflow 中的边：连接两个 WorkflowNode。
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)

    source_node_id: UUID = Field(foreign_key="workflownode.id", index=True)
    target_node_id: UUID = Field(foreign_key="workflownode.id", index=True)

    # UI 相关
    source_handle: str | None = None
    target_handle: str | None = None
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

    display: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    data: dict | str | list | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_by_id: UUID = Field(foreign_key="user.id", index=True)
    created_by: User = Relationship(back_populates="resources")

    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)
    workspace: Workspace = Relationship(back_populates="resources")


# --- 大模型 --


class LLMProvider(SQLModel, table=True):
    """Stores information about an LLM provider like OpenAI, Anthropic, or a local Ollama instance."""

    id: int | None = Field(default=None, primary_key=True)

    # A unique name for the provider, e.g., "openai", "anthropic", "ollama"
    name: str = Field(unique=True, index=True)

    # A user-friendly name for display in the UI, e.g., "OpenAI", "Anthropic"
    display_name: str

    # The base URL for API calls. E.g., "https://api.openai.com/v1"
    api_base_url: str

    # A link to the provider's documentation or where to get an API key
    documentation_url: str | None = None

    # Flag to indicate if this provider requires an API key from the user
    # True for OpenAI/Anthropic, False for a default local Ollama.
    requires_api_key: bool = Field(default=True)

    # --- Relationships ---
    # This provider has many models
    models: list["LLMModel"] = Relationship(back_populates="provider")

    # Many users can have credentials for this provider
    user_credentials: list["UserProviderCredential"] = Relationship(back_populates="provider")


class ModelType(str, Enum):
    """Enum for the type of model to guide how it should be used."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"


class LLMModel(SQLModel, table=True):
    """Stores details for a specific large language model."""

    id: int | None = Field(default=None, primary_key=True)

    # The exact name used in API calls, e.g., "gpt-4-turbo", "claude-3-opus-20240229"
    model_name: str = Field(index=True)

    # A user-friendly name for display, e.g., "GPT-4 Turbo", "Claude 3 Opus"
    display_name: str

    # The context window size for the model
    context_length: int

    # The type of model, useful for application logic
    model_type: ModelType = Field(default=ModelType.CHAT)

    # A flag to mark a system-wide default model for certain tasks
    is_default: bool = Field(default=False, index=True)

    # --- Relationships ---
    # The foreign key linking this model to its provider
    provider_id: int = Field(foreign_key="llmprovider.id")

    # The relationship back to the provider object
    provider: LLMProvider = Relationship(back_populates="models")


class UserProviderCredential(SQLModel, table=True):
    """
    Stores a user's encrypted API key for a specific LLM Provider.
    This is a many-to-many link between Users and LLMProviders.
    """

    id: int | None = Field(default=None, primary_key=True)

    # The encrypted API key, using the user's personal DEK
    encrypted_api_key: bytes = Field(sa_column=Column(LargeBinary))

    # --- Relationships ---
    user_id: UUID = Field(foreign_key="user.id")
    provider_id: int = Field(foreign_key="llmprovider.id")

    user: "User" = Relationship(back_populates="provider_credentials")
    provider: "LLMProvider" = Relationship(back_populates="user_credentials")


class Conversation(SQLModel, table=True):
    """
    业务层面的对话记录 (Thread)。
    它是 Checkpoint 的父级，用于权限控制和列表展示。
    """

    # 对应 LangGraph 的 thread_id
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, description="即 LangGraph 的 thread_id")

    workspace_id: UUID = Field(foreign_key="workspace.id", index=True)
    workspace: Workspace = Relationship()

    # 身份标识
    user_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    # 允许访客模式 (未登录用户)
    visitor_id: str | None = Field(default=None, index=True)

    title: str = Field(default="New Chat")

    # 统计信息 (可选，但推荐)
    message_count: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # 关系：一个对话有多个 Checkpoints (历史状态)
    checkpoints: list["LangGraphCheckpoint"] = Relationship(back_populates="conversation", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    # 关系：一个对话有多个 Writes (中间状态)
    writes: list["LangGraphCheckpointWrite"] = Relationship(back_populates="conversation", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class LangGraphCheckpoint(SQLModel, table=True):
    """
    映射 LangGraph 标准表 `checkpoints`。
    增加了 foreign_key 指向你的 Conversation 表，实现级联删除。
    """

    __tablename__ = "checkpoints"  # 强制使用 LangGraph 默认表名

    thread_id: str = Field(primary_key=True, foreign_key="conversation.id")

    # 复合主键 2: checkpoint_ns (命名空间，默认为空字符串)
    checkpoint_ns: str = Field(default="", primary_key=True)

    # 复合主键 3: checkpoint_id (UUID 字符串)
    checkpoint_id: str = Field(primary_key=True)

    # 上级指针
    parent_checkpoint_id: str | None = Field(default=None)

    type: str = Field(default="msgpack")

    # 核心数据 (Pickle 序列化)
    checkpoint: bytes = Field(sa_column=Column(LargeBinary))

    # 元数据
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", LargeBinary),  # 映射到数据库列名 "metadata"
    )

    # 关系回溯
    conversation: Conversation = Relationship(back_populates="checkpoints")


class LangGraphCheckpointWrite(SQLModel, table=True):
    """
    映射 LangGraph 标准表 `checkpoint_writes`。
    """

    __tablename__ = "writes"  # 强制使用 LangGraph 默认表名

    thread_id: str = Field(primary_key=True, foreign_key="conversation.id")
    checkpoint_ns: str = Field(default="", primary_key=True)
    checkpoint_id: str = Field(primary_key=True)
    task_id: str = Field(primary_key=True)
    idx: int = Field(primary_key=True)

    channel: str
    type: str = Field(default="msgpack")

    value: bytes = Field(sa_column=Column(LargeBinary))

    conversation: Conversation = Relationship(back_populates="writes")
