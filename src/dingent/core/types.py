import re
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field, FilePath, model_validator

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


# ---------------------------
# 新的工具输出建模
# ---------------------------


class ToolDisplayPayloadBase(BaseModel):
    """前端展示用的 Payload 基类"""

    type: str


class MarkdownPayload(ToolDisplayPayloadBase):
    type: Literal["markdown"] = "markdown"
    content: str


class TablePayload(ToolDisplayPayloadBase):
    type: Literal["table"] = "table"
    columns: list[str]
    rows: list[dict]
    title: str = ""


ToolDisplayPayload = MarkdownPayload | TablePayload


class ToolResult(BaseModel):
    """
    标准化后的工具输出。

    model_text:      （必填）给模型使用的精简文本（总结 / 提炼 / 结构说明）
    display:         （选填）前端富展示用的 payload 数组
    data:            （选填）结构化原始数据（前端/工作流/自动化二次使用）
    metadata:        （选填）附加元信息（执行耗时、来源、版本等）
    version:         协议/结构版本，方便将来升级
    """

    version: str = "1.0"
    model_text: str = Field(..., description="提供给 LLM 的简洁上下文文本")
    display: list[ToolDisplayPayload] = Field(default_factory=list, description="前端展示用 payload 列表")
    data: dict | str | list | None = Field(None, description="原始/结构化数据")
    metadata: dict = Field(default_factory=dict, description="元信息")

    @classmethod
    def from_any(cls, obj: str | dict) -> "ToolResult":
        """
        松散输入转标准 ToolResult:
        - str -> model_text + markdown display
        - dict -> 解析 keys
        - 已经是 ToolResult -> 原样返回
        """
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, str):
            return cls(
                model_text=obj,
                display=[MarkdownPayload(content=obj)],
            )
        if isinstance(obj, dict):
            # 允许不同 key 写法做一点点宽松兼容
            model_text = obj.get("model_text") or obj.get("model") or obj.get("text")

            if not isinstance(model_text, str):
                return cls(model_text=str(obj), display=[MarkdownPayload(content=str(obj))])

            # display
            raw_display = obj.get("display") or []
            display_payloads: list[ToolDisplayPayload] = []
            for p in raw_display:
                if not isinstance(p, dict):
                    continue
                p_type = p.get("type")
                try:
                    if p_type == "markdown":
                        display_payloads.append(MarkdownPayload(**p))
                    elif p_type == "table":
                        display_payloads.append(TablePayload(**p))
                    else:
                        # 未知类型先忽略或记录为 markdown
                        display_payloads.append(MarkdownPayload(content=f"[Unsupported payload type {p_type}] {p}"))
                except Exception as _:
                    display_payloads.append(MarkdownPayload(content=f"[Invalid payload] {p}"))

            data = obj.get("data")
            metadata = obj.get("metadata") or obj.get("meta") or {}

            # 若未提供 model_text，则尝试从 display 中推断
            if not model_text:
                if display_payloads:
                    first = display_payloads[0]
                    if isinstance(first, MarkdownPayload):
                        model_text = first.content[:1000]
                    elif isinstance(first, TablePayload):
                        model_text = f"表格:{first.title or '未命名'} 行数:{len(first.rows)} 列:{','.join(first.columns)}"
                elif data is not None:
                    model_text = f"返回数据 keys: {list(data.keys())[:10]}" if isinstance(data, dict) else "工具返回数据"
                else:
                    model_text = ""

            return cls(
                model_text=model_text,
                display=display_payloads,
                data=data,
                metadata=metadata,
            )

        return cls(
            model_text=str(obj),
            display=[MarkdownPayload(content=str(obj))],
        )

    def to_json_bytes(self) -> bytes:
        """
        Safely serializes the model to a JSON byte string using Pydantic's built-in method.
        """
        # model_dump_json() handles the conversion of the entire object,
        # including nested Pydantic models, into a JSON string.
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_json_bytes(cls, data: bytes) -> "ToolResult":
        """
        Safely deserializes a JSON byte string back into a ToolResult instance.
        """
        return cls.model_validate_json(data.decode("utf-8"))


class ExecutionModel(BaseModel):
    mode: Literal["local", "remote"] = Field(..., description="运行模式: 'local' 或 'remote'")
    url: str | None = None
    script_path: str | None = Field(None, description="插件管理器需要运行的Python入口文件路径")
    mcp_json_path: str | None = None

    @model_validator(mode="after")
    def check_exclusive_execution_mode(self) -> "ExecutionModel":
        return self


class ToolConfigModel(BaseModel):
    schema_path: FilePath = Field(..., description="指向一个包含用户配置Pydantic类的Python文件")


class WorkflowNodeData(BaseModel):
    assistantId: str = Field(..., description="Assistant ID referenced by this node")
    assistantName: str = Field(..., description="Assistant name for display")
    description: str | None = Field(None, description="Node description")
    isStart: bool = Field(False, description="Is this the start node")


class WorkflowNode(BaseModel):
    id: str = Field(..., description="Unique node identifier")
    type: Literal["assistant"] = Field("assistant", description="Node type")
    position: dict[str, float] = Field(..., description="Node position {x, y}")
    data: WorkflowNodeData = Field(..., description="Node data")


class WorkflowEdgeData(BaseModel):
    mode: Literal["single", "bidirectional"] = Field("single", description="Edge mode")


class WorkflowEdge(BaseModel):
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    sourceHandle: str | None = Field(None, description="Source handle ID")
    targetHandle: str | None = Field(None, description="Target handle ID")
    type: str | None = Field("default", description="Edge type")
    data: WorkflowEdgeData | None = Field(None, description="Edge data")


class WorkflowBase(BaseModel):
    id: str = Field(..., description="The unique and permanent ID for the workflow")
    name: str = Field(..., description="The display name for the workflow")
    description: str | None = Field(None, description="A description of what the workflow does")

    @model_validator(mode="before")
    @classmethod
    def _normalize_and_generate_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Step 1: Determine the source for the "display name".
            # It prioritizes a potential 'display_name' field, falling back to 'name' for compatibility.
            source_for_display_name = data.get("display_name") or data.get("name")

            if source_for_display_name:
                # Regardless of the source ('display_name' or 'name'), the final value
                # is assigned to the 'name' field that the model uses internally.
                data["name"] = source_for_display_name

            # Step 2: If an 'id' is not provided, generate it from the display name source.
            # This ensures that workflows without a pre-assigned ID get a deterministic one.
            if "id" not in data and source_for_display_name:
                data["id"] = generate_id_from_name(source_for_display_name)

        return data


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None


class Workflow(WorkflowBase):
    nodes: list[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="Workflow edges")
    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")
