from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic import Field as PydField
from sqlalchemy import JSON, Column, LargeBinary, Text
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


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


class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    guest = "guest"


class User(SQLModel, table=True):
    """
    用户模型：系统中的账户主体，所有用户资源都与此模型关联。
    """

    # 基本标识
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    username: str = Field(unique=True, index=True, description="唯一用户名（可显示/可登录）")
    email: str = Field(unique=True, index=True, description="用户邮箱（主要用于登录和通知）")
    role: UserRole = Field(default="user", description="用户角色，如 'user', 'admin', 'guest' 等")
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
    assistants: list["Assistant"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    workflows: list["Workflow"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    resources: list["Resource"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


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
    # tools_default_enabled: bool = True

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

    __table_args__ = (UniqueConstraint("user_id", "name", name="unique_user_assistant_name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(index=True)
    description: str | None = None
    version: str = "0.2.0"
    spec_version: str = "3.0"
    enabled: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # 外键：多对一 -> User
    user_id: UUID = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="assistants")

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


class PluginConfigSchema(SQLModel):
    name: str = Field(..., description="配置项的名称 (环境变量名)")
    type: Literal["string", "float", "integer", "bool"] = Field(..., description="配置项的期望类型 (e.g., 'string', 'number')")
    required: bool = Field(..., description="是否为必需项")
    secret: bool = Field(False, description="是否为敏感信息 (如 API Key)")
    description: str | None = Field(None, description="该配置项的描述")
    default: Any | None = Field(None, description="默认值 (如果存在)")


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

    config_schema: list[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

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
    user_id: UUID = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="workflows")

    # 关系
    nodes: list["WorkflowNode"] = Relationship(back_populates="workflow", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    edges: list["WorkflowEdge"] = Relationship(back_populates="workflow", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


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

    # 所有权：多对一 -> User
    user_id: UUID = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="resources")


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
