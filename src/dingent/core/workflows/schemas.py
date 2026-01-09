from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

from dingent.core.assistants.schemas import AssistantSpec
from dingent.core.utils import to_camel


class WorkflowNodeBase(SQLModel):
    """节点的基础共享字段"""

    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    is_start_node: bool = False
    type: str = "assistant"


class WorkflowNodeCreate(WorkflowNodeBase):
    """
    用于创建节点。
    前端在 POST /workflows/{workflow_id}/nodes 时发送此模型。
    workflow_id 从 URL 中获取，不需要在 body 中提供。
    """

    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    measured: dict[str, float] = {}
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    is_start_node: bool = False
    type: str = "assistant"
    id: str = Field(
        description="节点在前端，用于识别edge连接的节点，数据库中的id是自动生成的UUID，不使用此字段。",
    )
    assistant_id: UUID | None = None


class WorkflowNodeUpdate(SQLModel):
    """
    用于更新节点。
    前端在 PATCH /workflows/{workflow_id}/nodes/{node_id} 时发送此模型。
    通常只允许更新位置等 UI 相关属性。
    """

    position: dict[str, float] | None = None
    is_start_node: bool | None = None


class WorkflowNodeRead(WorkflowNodeBase):
    """用于从 API 读取节点数据。"""

    id: UUID
    name: str
    assistant_id: UUID
    workflow_id: UUID
    position: dict[str, float]


# ==============================================================================
# WorkflowEdge Models
# ==============================================================================


class WorkflowEdgeBase(SQLModel):
    """边的基础共享字段"""

    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    source_node_id: str | UUID
    target_node_id: str | UUID
    source_handle: str | None = None
    target_handle: str | None = None
    type: str = "directional"
    mode: Literal["single", "bidirectional"] = "single"


class WorkflowEdgeCreate(WorkflowEdgeBase):
    """
    用于创建边。
    前端在 POST /workflows/{workflow_id}/edges 时发送此模型。
    """

    model_config = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    pass


class WorkflowEdgeUpdate(SQLModel):
    """
    用于更新边。
    通常边很少被更新，一般是删除后重建。但可以预留接口。
    """

    source_handle: str | None = None
    target_handle: str | None = None
    type: str | None = None


class WorkflowEdgeRead(WorkflowEdgeBase):
    """用于从 API 读取边数据。"""

    id: UUID
    workflow_id: UUID


# ==============================================================================
# Workflow Models
# ==============================================================================


class WorkflowBase(SQLModel):
    """工作流的基础共享字段"""

    description: str | None = None


class WorkflowCreate(WorkflowBase):
    """
    用于创建工作流。
    前端在 POST /workflows 时发送此模型。
    user_id 从认证信息中获取。
    """

    name: str

    pass


class WorkflowReplace(WorkflowBase):
    """
    用于替换整个工作流，包括其节点和边。
    前端在 PUT /workflows/{workflow_id} 时发送此模型。
    注意：这会覆盖现有的节点和边。
    """

    name: str
    nodes: list[WorkflowNodeCreate] = []
    edges: list[WorkflowEdgeCreate] = []


class WorkflowUpdate(WorkflowBase):
    """
    用于更新工作流元数据（名称、描述）。
    前端在 PATCH /workflows/{workflow_id} 时发送此模型。
    注意：节点的修改不在这里处理，而是通过专门的节点接口。
    """

    name: str | None = None


class WorkflowReadBasic(WorkflowBase):
    """
    用于在列表中读取工作流的基础信息。
    不包含 nodes 和 edges，避免数据冗余。
    """

    workspace_id: UUID

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class WorkflowRead(WorkflowReadBasic):
    """
    用于读取单个工作流的完整信息，包含其所有的节点和边。
    前端在 GET /workflows/{workflow_id} 时会收到此模型。
    """

    workspace_id: UUID

    nodes: list[WorkflowNodeRead] = []
    edges: list[WorkflowEdgeRead] = []


class NodeSpec(WorkflowNodeBase):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str


class EdgeSpec(SQLModel):
    id: UUID = Field(default_factory=uuid4)
    source_name: str
    target_name: str


class ExecutableWorkflow(SQLModel):
    """
    这是传给 GraphFactory 的纯数据对象。
    它不需要 workspace_id, user_id 等数据库外键。
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    start_node: str
    description: str | None = None
    assistant_configs: dict[str, AssistantSpec] = {}
    adjacency_map: dict[str, list[str]]
