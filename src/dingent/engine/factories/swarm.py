import re
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Callable

from dingent.core.schemas import WorkflowSpec
from dingent.core.factories.assistant_factory import AssistantFactory
from dingent.core.utils import normalize_agent_name
from dingent.engine.agents.simple_agent import build_simple_react_agent
from dingent.engine.agents.tools import create_handoff_tool, mcp_tool_wrapper


@asynccontextmanager
async def create_assistant_graphs(
    assistant_factory: AssistantFactory,
    workflow: WorkflowSpec,
    llm,
    log_method: Callable,
):
    assistants_runtime = {}

    # 1. 初始化 Runtime
    for node in workflow.nodes:
        rt = await assistant_factory.create_runtime(node.assistant)
        assistants_runtime[node.assistant.name] = rt

    name_map = {orig: normalize_agent_name(orig) for orig in assistants_runtime}

    # 2. 预创建所有 Handoff 工具
    handoff_registry = {}
    for orig_name, rt in assistants_runtime.items():
        norm_name = name_map[orig_name]
        handoff_registry[norm_name] = create_handoff_tool(agent_name=norm_name, description=f"Transfer to {orig_name}. {rt.description}", log_method=log_method)

    assistant_graphs = {}

    # 3. 构建每个 Agent 图
    async with AsyncExitStack() as stack:
        for orig_name, rt in assistants_runtime.items():
            norm_name = name_map[orig_name]

            # 加载 MCP 工具并包装
            raw_tools = await stack.enter_async_context(rt.load_tools())
            wrapped_tools = [mcp_tool_wrapper(t, log_method) for t in raw_tools]

            # 筛选相关的 Handoff 工具
            valid_dests = [d for d in rt.destinations if d in name_map]
            handoff_tools = [handoff_registry[name_map[d]] for d in valid_dests]

            # 构建 Agent
            agent = build_simple_react_agent(
                name=norm_name,
                llm=llm,
                tools=handoff_tools + wrapped_tools,
                system_prompt=rt.description,
            )
            assistant_graphs[norm_name] = agent

        yield assistant_graphs
