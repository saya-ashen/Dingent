import json
from collections.abc import Callable
from typing import Annotated, Any, cast

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, StructuredTool, tool
from langgraph.types import Command
from mcp.types import TextContent
from pydantic import BaseModel, Field, create_model

from dingent.core.schemas import RunnableTool

# --- 动态 Pydantic 模型构建 (优化版) ---
JSON_TYPE_MAP = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "number": float,
    "array": list,
    "object": dict,
    "null": type(None),
    "any": Any,
}


def create_dynamic_pydantic_class(
    base_class: type[BaseModel],
    schema_dict: dict,
    name: str,
) -> type[BaseModel]:
    fields = {}
    properties = schema_dict.get("properties", {})
    required_fields = set(schema_dict.get("required", []))

    # 处理额外属性配置
    model_config = {}
    if schema_dict.get("additionalProperties", True) is False:
        model_config["extra"] = "forbid"

    for field_name, field_info in properties.items():
        json_type = field_info.get("type", "any")
        python_type = JSON_TYPE_MAP.get(json_type, Any)

        # 必需字段使用 ...，可选字段默认 None
        default = ... if field_name in required_fields else None

        fields[field_name] = (
            python_type if field_name in required_fields else python_type | None,
            Field(default=default, title=field_info.get("title"), description=field_info.get("description")),
        )

    return create_model(name, __base__=base_class, __config__=model_config, **fields)


def mcp_tool_wrapper(runnable_tool: RunnableTool, log_method: Callable) -> StructuredTool:
    tool_def = runnable_tool.tool

    async def call_tool(tool_call_id: Annotated[str, InjectedToolCallId], **kwargs) -> Command:
        try:
            response_raw = await runnable_tool.run(kwargs)
            log_method("info", f"Tool Call Result: {response_raw}", context={"tool": tool_def.name, "id": tool_call_id})
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            log_method("error", f"Error: {error_msg}", context={"tool": tool_def.name, "id": tool_call_id})
            # 出错时返回普通消息，保持流程继续
            return Command(update={"messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id, status="error")]})

        # 解析 Artifacts
        contents: list[TextContent] = response_raw.content
        model_text = "Empty response."
        artifact = None

        if contents and isinstance(contents[0], TextContent):
            raw_text = contents[0].text
            try:
                # 尝试解析结构化数据中的 artifact
                data = json.loads(raw_text) if raw_text else {}
                artifact = cast(dict[str, list[dict]], data.get("display"))
                model_text = data.get("model_text", raw_text)
            except json.JSONDecodeError:
                model_text = raw_text
        tool_message = ToolMessage(content=model_text, tool_call_id=tool_call_id, artifact=artifact)
        tool_message.name = tool_def.name

        # 这里的 Command 只包含增量更新
        return Command(
            update={
                "messages": [tool_message],
            },
        )

    # 构建 Schema
    class ToolArgsSchema(BaseModel):
        tool_call_id: Annotated[str, InjectedToolCallId]

    CombinedSchema = create_dynamic_pydantic_class(ToolArgsSchema, tool_def.inputSchema, name=f"Args_{tool_def.name}")

    return StructuredTool(
        name=tool_def.name,
        description=tool_def.description or "",
        args_schema=CombinedSchema,
        coroutine=call_tool,
        tags=[runnable_tool.plugin_name],
    )


# --- Handoff Tool ---
def create_handoff_tool(agent_name: str, description: str | None, log_method: Callable) -> BaseTool:
    tool_name = f"transfer_to_{agent_name}"

    @tool(tool_name, description=description)
    async def handoff_tool(tool_call_id: Annotated[str, InjectedToolCallId]):
        log_method("info", f"Handoff to {agent_name}", context={"id": tool_call_id})
        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={"messages": [ToolMessage(content=f"Transferred to {agent_name}", tool_call_id=tool_call_id, name=tool_name)]},
        )

    return handoff_tool
