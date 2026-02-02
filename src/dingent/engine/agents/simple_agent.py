import json
from typing import Annotated, Any, Awaitable, Sequence, cast, override
from deepagents.graph import (
    BASE_AGENT_PROMPT,
    AnthropicPromptCachingMiddleware,
    BackendFactory,
    BackendProtocol,
    BaseCache,
    HumanInTheLoopMiddleware,
    InterruptOnConfig,
    PatchToolCallsMiddleware,
    ResponseFormat,
    SkillsMiddleware,
    StateBackend,
    SummarizationMiddleware,
    get_default_model,
)
from langchain.agents import AgentState, create_agent
from deepagents import CompiledSubAgent, FilesystemMiddleware, MemoryMiddleware, SubAgent, SubAgentMiddleware


from langchain.agents.middleware.todo import WRITE_TODOS_SYSTEM_PROMPT, WRITE_TODOS_TOOL_DESCRIPTION, Todo
from langchain.agents.middleware.types import ModelCallResult, ToolCallRequest
from langchain.chat_models import init_chat_model
from langchain.tools import BaseTool, InjectedToolCallId, tool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer, Command

from .messages import ActivityMessage
from .state import SimpleAgentState
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, TodoListMiddleware
from langchain.agents import create_agent
from langgraph.runtime import Runtime
from typing import Any, Callable


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


class PluginConfigMiddleware(AgentMiddleware):
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        all_messages = request.messages
        filtered_messages: list[AnyMessage] = [msg for msg in all_messages if isinstance(msg, (SystemMessage, HumanMessage, AIMessage, ToolMessage))]
        request.messages = filtered_messages
        result = await handler(request)

        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """
        统一处理：
        1. 输入前：注入 plugin_configs
        2. 输出后：处理 MCP Artifacts 并生成 AGUI Display 消息
        3. 输出后：处理 Command (Handoff)
        """

        # --- 1. (Before) 输入拦截：注入配置 ---
        # 获取当前运行时的配置
        runtime = request.runtime

        config = runtime.config
        plugin_configs = config.get("configurable", {}).get("assistant_plugin_configs", {})

        tool = request.tool
        # assert tool is not None, "Tool must be present in the request."
        if not tool:
            return await handler(request)
        args = request.tool_call.get("args", {}).copy()

        # 检查 Tags 并注入配置
        if tool.tags and (plugin_name := tool.tags[0]):
            if cfg := plugin_configs.get(plugin_name):
                if len(cfg.get("config", {})) > 0:
                    args["plugin_config"] = cfg.get("config")
                    # 更新请求参数
                    request.tool_call["args"] = args

        try:
            # --- 2. (Execute) 执行工具 ---
            # 调用 handler 执行实际的工具逻辑
            result = await handler(request)

            try:
                artifact = result.update.get("messages")[-1].artifact
            except:
                artifact = None
            try:
                todos = result.update.get("todos")
            except:
                todos = None
            if not artifact and not todos:
                return result

            tool_call_id = request.tool_call.get("id") or "unknown_tool_call_id"
            tool_name = tool.name

            collected_messages = []

            tool_msg = result.update.get("messages")[-1]
            collected_messages.append(tool_msg)

            if artifact:
                agui_display = mcp_artifact_to_agui_display(
                    tool_name=tool_name,
                    query_args=args,
                    surface_base_id=tool_call_id,
                    artifact=artifact,
                )
                collected_messages.append(ActivityMessage(content=agui_display))

            return Command(update={"messages": collected_messages})

        except Exception as e:
            # 统一错误处理
            return Command(update={"messages": [ToolMessage(content=f"Execution Error: {str(e)}", tool_call_id=request.tool_call.get("id"), is_error=True)]})


class FilteredSummarizationMiddleware(SummarizationMiddleware):
    @override
    def before_model(
        self,
        state: AgentState[Any],
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        messages = state["messages"]
        filtered_messages: list[AnyMessage] = [msg for msg in messages if isinstance(msg, (SystemMessage, HumanMessage, AIMessage, ToolMessage))]
        state["messages"] = filtered_messages
        return super().before_model(state, runtime)

    @override
    async def abefore_model(
        self,
        state: AgentState[Any],
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        messages = state["messages"]
        filtered_messages: list[AnyMessage] = [msg for msg in messages if isinstance(msg, (SystemMessage, HumanMessage, AIMessage, ToolMessage))]
        state["messages"] = filtered_messages
        return await super().abefore_model(state, runtime)


class JsonTodoListMiddleware(TodoListMiddleware):
    """
    A subclass of TodoListMiddleware that ensures the `write_todos` tool
    returns a valid JSON string result, fixing frontend parsing issues.
    """

    def __init__(
        self,
        *,
        system_prompt: str = WRITE_TODOS_SYSTEM_PROMPT,
        tool_description: str = WRITE_TODOS_TOOL_DESCRIPTION,
    ) -> None:
        # 初始化父类
        super().__init__(system_prompt=system_prompt, tool_description=tool_description)

        # 重新定义 write_todos 工具，覆盖父类的实现
        @tool(description=self.tool_description)
        def write_todos(todos: list[Todo], tool_call_id: Annotated[str, InjectedToolCallId]) -> Command[Any]:
            """Create and manage a structured task list for your current work session."""

            todos_json = json.dumps(todos, ensure_ascii=False)

            result_payload = json.dumps(
                {
                    "message": "Updated todo list successfully",
                    "todos": json.loads(todos_json),  # 确保它是对象不是二次转义的字符串
                },
                ensure_ascii=False,
            )

            return Command(
                update={
                    "todos": todos,
                    "messages": [ToolMessage(result_payload, tool_call_id=tool_call_id)],
                }
            )

        # 将覆盖后的工具赋值给 self.tools
        self.tools = [write_todos]


def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    response_format: ResponseFormat | None = None,
    context_schema: type[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph:
    """Create a deep agent.

    !!! warning "Deep agents require a LLM that supports tool calling!"

    By default, this agent has access to the following tools:

    - `write_todos`: manage a todo list
    - `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`: file operations
    - `execute`: run shell commands
    - `task`: call subagents

    The `execute` tool allows running shell commands if the backend implements `SandboxBackendProtocol`.
    For non-sandbox backends, the `execute` tool will return an error message.

    Args:
        model: The model to use.

            Defaults to `claude-sonnet-4-5-20250929`.

            Use the `provider:model` format (e.g., `openai:gpt-5`) to quickly switch between models.
        tools: The tools the agent should have access to.

            In addition to custom tools you provide, deep agents include built-in tools for planning,
            file management, and subagent spawning.
        system_prompt: Custom system instructions to prepend before the base deep agent
            prompt.

            If a string, it's concatenated with the base prompt.
        middleware: Additional middleware to apply after the standard middleware stack
            (`TodoListMiddleware`, `FilesystemMiddleware`, `SubAgentMiddleware`,
            `SummarizationMiddleware`, `AnthropicPromptCachingMiddleware`,
            `PatchToolCallsMiddleware`).
        subagents: The subagents to use.

            Each subagent should be a `dict` with the following keys:

            - `name`
            - `description` (used by the main agent to decide whether to call the sub agent)
            - `prompt` (used as the system prompt in the subagent)
            - (optional) `tools`
            - (optional) `model` (either a `LanguageModelLike` instance or `dict` settings)
            - (optional) `middleware` (list of `AgentMiddleware`)
        skills: Optional list of skill source paths (e.g., `["/skills/user/", "/skills/project/"]`).

            Paths must be specified using POSIX conventions (forward slashes) and are relative
            to the backend's root. When using `StateBackend` (default), provide skill files via
            `invoke(files={...})`. With `FilesystemBackend`, skills are loaded from disk relative
            to the backend's `root_dir`. Later sources override earlier ones for skills with the
            same name (last one wins).
        memory: Optional list of memory file paths (`AGENTS.md` files) to load
            (e.g., `["/memory/AGENTS.md"]`).

            Display names are automatically derived from paths.

            Memory is loaded at agent startup and added into the system prompt.
        response_format: A structured output response format to use for the agent.
        context_schema: The schema of the deep agent.
        checkpointer: Optional `Checkpointer` for persisting agent state between runs.
        store: Optional store for persistent storage (required if backend uses `StoreBackend`).
        backend: Optional backend for file storage and execution.

            Pass either a `Backend` instance or a callable factory like `lambda rt: StateBackend(rt)`.
            For execution support, use a backend that implements `SandboxBackendProtocol`.
        interrupt_on: Mapping of tool names to interrupt configs.

            Pass to pause agent execution at specified tool calls for human approval or modification.

            Example: `interrupt_on={"edit_file": True}` pauses before every edit.
        debug: Whether to enable debug mode. Passed through to `create_agent`.
        name: The name of the agent. Passed through to `create_agent`.
        cache: The cache to use for the agent. Passed through to `create_agent`.

    Returns:
        A configured deep agent.
    """
    if model is None:
        model = get_default_model()
    elif isinstance(model, str):
        model = init_chat_model(model)

    if model.profile is not None and isinstance(model.profile, dict) and "max_input_tokens" in model.profile and isinstance(model.profile["max_input_tokens"], int):
        trigger = ("fraction", 0.85)
        keep = ("fraction", 0.10)
        truncate_args_settings = {
            "trigger": ("fraction", 0.85),
            "keep": ("fraction", 0.10),
        }
    else:
        trigger = ("tokens", 170000)
        keep = ("messages", 6)
        truncate_args_settings = {
            "trigger": ("messages", 20),
            "keep": ("messages", 20),
        }

    # Build middleware stack for subagents (includes skills if provided)
    subagent_middleware: list[AgentMiddleware] = [
        JsonTodoListMiddleware(),
    ]

    backend = backend if backend is not None else (lambda rt: StateBackend(rt))

    if skills is not None:
        subagent_middleware.append(SkillsMiddleware(backend=backend, sources=skills))
    subagent_middleware.extend(
        [
            FilesystemMiddleware(backend=backend),
            FilteredSummarizationMiddleware(
                model=model,
                backend=backend,
                trigger=trigger,
                keep=keep,
                trim_tokens_to_summarize=None,
                truncate_args_settings=cast(Any, truncate_args_settings),
            ),
            AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
            PatchToolCallsMiddleware(),
        ]
    )

    # Build main agent middleware stack
    deepagent_middleware: list[AgentMiddleware] = [
        JsonTodoListMiddleware(),
    ]
    if memory is not None:
        deepagent_middleware.append(MemoryMiddleware(backend=backend, sources=memory))
    if skills is not None:
        deepagent_middleware.append(SkillsMiddleware(backend=backend, sources=skills))
    deepagent_middleware.extend(
        [
            FilesystemMiddleware(backend=backend),
            SubAgentMiddleware(
                default_model=model,
                default_tools=tools,
                subagents=subagents if subagents is not None else [],
                default_middleware=subagent_middleware,
                default_interrupt_on=interrupt_on,
                general_purpose_agent=True,
            ),
            FilteredSummarizationMiddleware(
                model=model,
                backend=backend,
                trigger=trigger,
                keep=keep,
                trim_tokens_to_summarize=None,
                truncate_args_settings=cast(Any, truncate_args_settings),
            ),
            AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
            PatchToolCallsMiddleware(),
        ]
    )
    if middleware:
        deepagent_middleware.extend(middleware)
    if interrupt_on is not None:
        deepagent_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    # Combine system_prompt with BASE_AGENT_PROMPT
    if system_prompt is None:
        final_system_prompt: str | SystemMessage = BASE_AGENT_PROMPT
    elif isinstance(system_prompt, SystemMessage):
        # SystemMessage: append BASE_AGENT_PROMPT to content_blocks
        new_content = [
            *system_prompt.content_blocks,
            {"type": "text", "text": f"\n\n{BASE_AGENT_PROMPT}"},
        ]
        final_system_prompt = SystemMessage(content=new_content)
    else:
        # String: simple concatenation
        final_system_prompt = system_prompt + "\n\n" + BASE_AGENT_PROMPT

    return create_agent(
        model,
        system_prompt=final_system_prompt,
        tools=tools,
        middleware=deepagent_middleware,
        response_format=response_format,
        context_schema=context_schema,
        checkpointer=checkpointer,
        store=store,
        debug=debug,
        name=name,
        cache=cache,
    ).with_config({"recursion_limit": 1000})


middleware = [PluginConfigMiddleware()]


def build_simple_react_agent(
    name: str,
    llm: BaseChatModel,
    tools: list[StructuredTool],
    system_prompt: str | None = None,
    max_iterations: int = 6,
) -> CompiledStateGraph:
    # 使用 create_react_agent 并传入 middleware
    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
    )
    agent.name = name
    return agent
