import json
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from langgraph.types import Command

from .messages import ActivityMessage
from .state import SimpleAgentState


def mcp_artifact_to_agui_display(tool_name, query_args: dict, surface_base_id: str | list[str], artifact: list[dict[str, Any]], update_data=False) -> dict[str, list[dict]]:
    if not isinstance(artifact, list):
        return [artifact]
    else:
        return cast(Any, artifact)
    agui_display = {"operations": []}

    if isinstance(surface_base_id, list):
        assert len(surface_base_id) == len(artifact), "Surface base ID and artifact length mismatch"

    for i, item in enumerate(artifact):
        # 1. 基础渲染信号
        surface_id = f"{surface_base_id}-{i}" if isinstance(surface_base_id, str) else surface_base_id[i]

        type_ = item.get("type")
        if update_data:
            columns = item.get("columns", [])  # 预期格式: [{"key": "id", "label": "ID"}, ...]
            rows = item.get("rows", [])
            title = item.get("title", "Table Data")
            a2ui_rows = _transform_rows_to_a2ui(columns, rows)
            agui_display["operations"].append(
                {
                    "dataModelUpdate": {
                        "surfaceId": surface_id,
                        "contents": [
                            {"key": "rows", "valueMap": a2ui_rows},
                            # 初始化分页状态
                            {"key": "pageInfo", "valueString": "Page 1"},
                            {"key": "isFirstPage", "valueBoolean": True},
                            {"key": "isLastPage", "valueBoolean": False},
                        ],
                    }
                }
            )
            break

        # === 处理文本类型 ===
        if type_ == "text":
            raise NotImplementedError("Text type rendering not implemented in this snippet.")

        # === 处理表格类型 ===
        elif type_ == "table":
            columns = item.get("columns", [])  # 预期格式: [{"key": "id", "label": "ID"}, ...]
            rows = item.get("rows", [])
            title = item.get("title", "Table Data")

            # --- A. 动态构建组件列表 ---
            components = []

            # 1. Root Container (包含标题、表头、列表、分页)
            components.append(
                {
                    "id": "root",
                    "component": {
                        "Column": {"children": {"explicitList": ["tableTitle", "tableHeader", "tableBody", "paginationRow"]}, "alignment": "stretch", "distribution": "start"}
                    },
                }
            )

            # 2. Table Title
            components.append({"id": "tableTitle", "component": {"Text": {"text": {"literalString": title}, "usageHint": "h3"}}})

            # 3. 动态表头 (Header Row)
            header_child_ids = []
            for col in columns:
                col_id = f"header_{col}"
                header_child_ids.append(col_id)
                components.append(
                    {
                        "id": col_id,
                        "component": {
                            "Text": {
                                "text": {"literalString": col},
                                "usageHint": "caption",
                                "weight": 1,  # 均匀分布
                            }
                        },
                    }
                )

            components.append({"id": "tableHeader", "component": {"Row": {"children": {"explicitList": header_child_ids}, "distribution": "spaceBetween", "alignment": "center"}}})

            # 4. 动态行模板 (Row Template)
            # 这里是关键：template 中的组件绑定相对路径
            row_child_ids = []
            for col in columns:
                cell_id = f"cell_{col}"
                row_child_ids.append(cell_id)
                components.append(
                    {
                        "id": cell_id,
                        "component": {
                            "Text": {
                                # 动态绑定：如果列key是 "email"，路径就是 "/email"
                                "text": {"path": f"/{col}"},
                                "weight": 1,
                            }
                        },
                    }
                )

            components.append({"id": "rowTemplate", "component": {"Row": {"children": {"explicitList": row_child_ids}, "distribution": "spaceBetween", "alignment": "center"}}})

            # 5. 列表容器 (The List)
            components.append(
                {
                    "id": "tableBody",
                    "component": {
                        "List": {
                            "children": {
                                "template": {
                                    "componentId": "rowTemplate",
                                    "dataBinding": "/rows",  # 绑定到数据模型的 /rows 数组
                                }
                            },
                            "direction": "vertical",
                        }
                    },
                }
            )

            # 6. 分页控件
            page_number = int(query_args.get("page", 1))
            components.extend(
                [
                    {
                        "id": "paginationRow",
                        "component": {"Row": {"children": {"explicitList": ["prevBtn", "pageInfo", "nextBtn"]}, "distribution": "center", "alignment": "center"}},
                    },
                    {
                        "id": "prevBtn",
                        "component": {
                            "Button": {
                                "child": "prevBtnText",
                                "action": {
                                    "name": tool_name,
                                    "context": [
                                        {
                                            "key": "query_args",
                                            "value": {"literalString": json.dumps({**query_args, "page": page_number})},
                                        }
                                    ],
                                },
                                "disabled": {"path": "/isFirstPage"},
                            }
                        },
                    },
                    {"id": "prevBtnText", "component": {"Text": {"text": {"literalString": "Previous"}}}},
                    {"id": "pageInfo", "component": {"Text": {"text": {"path": "/pageInfo"}, "usageHint": "caption"}}},
                    {
                        "id": "nextBtn",
                        "component": {
                            "Button": {
                                "child": "nextBtnText",
                                "action": {
                                    "name": tool_name,
                                    "context": [
                                        {
                                            "key": "query_args",
                                            "value": {"literalString": json.dumps({**query_args, "page": page_number + 2})},
                                        }
                                    ],
                                },
                                "disabled": {"path": "/isLastPage"},
                            }
                        },
                    },
                    {"id": "nextBtnText", "component": {"Text": {"text": {"literalString": "Next"}}}},
                ]
            )

            # 添加 SurfaceUpdate 消息
            agui_display["operations"].append({"surfaceUpdate": {"surfaceId": surface_id, "components": components}})

            # --- B. 数据模型转换 ---
            # 将 Python 字典列表转换为 A2UI 的 adjacency list 格式
            a2ui_rows = _transform_rows_to_a2ui(columns, rows)

            # 添加 DataModelUpdate 消息
            agui_display["operations"].append(
                {
                    "dataModelUpdate": {
                        "surfaceId": surface_id,
                        "contents": [
                            {"key": "rows", "valueMap": a2ui_rows},
                            # 初始化分页状态
                            {"key": "pageInfo", "valueString": "Page 1"},
                            {"key": "isFirstPage", "valueBoolean": True},
                            {"key": "isLastPage", "valueBoolean": False},
                        ],
                    }
                }
            )
        if not update_data:
            agui_display["operations"].append({"beginRendering": {"surfaceId": surface_id, "root": "root", "styles": {"primaryColor": "#1976D2", "font": "Roboto"}}})

    return agui_display


def _transform_rows_to_a2ui(columns: list[str], rows: list[list[str | int | Any]]) -> list[dict]:
    """
    辅助函数：将 [{'id': 1, 'name': 'A'}] 转换为 A2UI 的 valueMap 结构
    A2UI 数组本质上是一个 Map，Key 是索引字符串 "0", "1", ...
    """
    a2ui_list = []
    for idx, row_data in enumerate(rows):
        # 构建每一行的数据对象
        row_fields = []
        for k, v in zip(columns, row_data, strict=False):
            entry: dict[str, Any] = {"key": k}
            # 根据类型填充 valueString, valueNumber 等
            if isinstance(v, bool):
                entry["valueBoolean"] = v
            elif isinstance(v, int | float):
                entry["valueNumber"] = v
            else:
                entry["valueString"] = str(v)
            row_fields.append(entry)

        # 将行数据放入列表，Key 是索引
        a2ui_list.append({"key": str(idx), "valueMap": row_fields})
    return a2ui_list


def build_simple_react_agent(
    name: str,
    llm: BaseChatModel,
    tools: list[StructuredTool],
    system_prompt: str | None = None,
    max_iterations: int = 6,
    stop_when_no_tool: bool = True,
) -> CompiledStateGraph:
    name_to_tool = {t.name: t for t in tools}
    LLM_SAFE_TYPES = (SystemMessage, HumanMessage, AIMessage, ToolMessage)

    async def model_node(state: SimpleAgentState, config: RunnableConfig) -> dict[str, Any]:
        iteration = state.get("iteration", 0)
        # 简单的循环保护
        if iteration >= max_iterations:
            return {"messages": [AIMessage(content="Max iterations reached.")]}

        all_messages = state.get("messages", [])
        filtered_messages = [msg for msg in all_messages if isinstance(msg, LLM_SAFE_TYPES)]

        if system_prompt:
            input_messages = [SystemMessage(content=system_prompt)] + filtered_messages
        else:
            input_messages = filtered_messages

        bound_model = llm.bind_tools(tools)

        aggregated_message = None

        async for chunk in bound_model.astream(input_messages, config=config):
            if aggregated_message is None:
                aggregated_message = chunk
            else:
                aggregated_message += chunk

        if aggregated_message is None:
            aggregated_message = AIMessage(content="")

        return {
            "messages": [aggregated_message],
            "iteration": iteration + 1,
        }

    async def tools_node(state: SimpleAgentState, config: RunnableConfig) -> Command:
        last_msg = state.get("messages", [])[-1]
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return Command(update={})

        # 获取插件配置
        plugin_configs = config.get("configurable", {}).get("assistant_plugin_configs", {})

        # 用于收集本轮循环中产生的"普通"消息（非 Handoff）
        collected_messages: list[BaseMessage] = []

        for tc in last_msg.tool_calls:
            tool_name = tc["name"]
            tool = name_to_tool.get(tool_name)

            # 1. 处理工具不存在的情况
            if not tool:
                collected_messages.append(ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tc["id"], is_error=True))
                continue

            # 2. 注入配置参数
            args = tc.get("args", {}).copy()
            if tool.tags and (plugin_name := tool.tags[0]):
                if cfg := plugin_configs.get(plugin_name):
                    if len(cfg.get("config", {})) > 0:
                        args["plugin_config"] = cfg.get("config")

            try:
                # 3. 执行工具
                result = await tool.ainvoke(
                    {
                        "id": tc["id"],
                        "name": tool_name,
                        "args": args,
                        "tool_call_id": tc["id"],
                        "type": "tool_call",
                    }
                )

                if not isinstance(result, Command):
                    raise ValueError(f"Tool {tool_name} did not return a Command object.")

                if result.graph:
                    # 1. 获取当前所有的历史消息
                    all_current_messages: list = list(state.get("messages", []))

                    all_current_messages.extend(collected_messages)

                    handoff_tool_msgs = result.update.get("messages", [])
                    all_current_messages.extend(handoff_tool_msgs)

                    return Command(
                        goto=result.goto,
                        graph=result.graph,
                        update={
                            "messages": all_current_messages,
                        },
                    )

                else:
                    raw_updates = result.update.get("messages", [])
                    for msg in raw_updates:
                        if msg.type == "tool":
                            # 处理 MCP Artifacts
                            artifact = getattr(msg, "artifact", None)
                            if not artifact:
                                collected_messages.append(msg)
                                continue

                            # 生成 AGUI Display
                            agui_display = mcp_artifact_to_agui_display(
                                tool_name=tool_name,
                                query_args=tc.get("args", {}),
                                surface_base_id=msg.tool_call_id,
                                artifact=artifact,
                            )
                            collected_messages.append(msg)
                            collected_messages.append(ActivityMessage(content=agui_display))
                        else:
                            # 非 ToolMessage 直接添加 (例如额外的 AIMessage)
                            collected_messages.append(msg)

            except Exception as e:
                collected_messages.append(ToolMessage(content=f"Execution Error: {str(e)}", tool_call_id=tc["id"], is_error=True))

        # 循环结束，没有触发 Handoff，返回本轮所有工具的增量更新
        return Command(
            update={
                "messages": collected_messages,
            }
        )

    def route_after_model(state: SimpleAgentState):
        messages = state.get("messages", [])
        if not messages:
            return END

        last_msg = messages[-1]
        has_tool_calls = isinstance(last_msg, AIMessage) and bool(last_msg.tool_calls)

        if has_tool_calls and state.get("iteration", 0) <= max_iterations:
            return "tools"

        if stop_when_no_tool or not has_tool_calls:
            return END

        return END

    async def ui_node(state: SimpleAgentState) -> Command:
        action = state.get("a2ui_action", {})
        user_action = action.get("userAction", {})
        if not user_action:
            raise ValueError("No user_action found in a2ui_action")

        tool_name = user_action.get("name")
        if tool_name and tool_name in name_to_tool:
            tool = name_to_tool[tool_name]
            context = user_action.get("context", {})
            surface_id = context.get("surfaceId", "")
            surface_base_id = "-".join(surface_id.split("-")[:-1])
            query_args = json.loads(context.get("query_args", "{}"))
            # FIXME: query_args还要加上工具的配置参数
            result = await tool.ainvoke(
                {
                    "id": "agui_action",
                    "name": tool_name,
                    "args": query_args,
                    "tool_call_id": "agui_action",
                    "type": "tool_call",
                }
            )
            tool_message = result.update.get("messages", [])[0]
            artifact = tool_message.artifact
            if artifact:
                agui_display = mcp_artifact_to_agui_display(
                    tool_name,
                    query_args,
                    surface_base_id=surface_base_id,
                    artifact=artifact,
                    update_data=True,
                )
                return Command(
                    update={
                        "messages": [
                            tool_message,
                            ActivityMessage(content=[agui_display]),
                        ]
                    },
                    goto=END,
                )

        return Command(goto="model")

    def route_entry(state: SimpleAgentState):
        # 如果状态中有 UI 动作，优先进入 UI 处理节点
        if state.get("a2ui_action"):
            return "ui_handler"
        return "model"

    workflow = StateGraph(SimpleAgentState)
    workflow.add_node("model", model_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("ui_handler", ui_node)
    workflow.set_conditional_entry_point(
        route_entry,
        {
            "ui_handler": "ui_handler",
            "model": "model",
        },
    )
    workflow.add_conditional_edges("model", route_after_model)
    workflow.add_edge("tools", "model")

    compiled = workflow.compile()
    compiled.name = name
    return compiled
