from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager

from langchain_core.tools import BaseTool

from dingent.core.factories.assistant_factory import AssistantFactory
from dingent.core.runtime.assistant import AssistantRuntime
from dingent.core.schemas import AssistantSpec, ExecutableWorkflow
from dingent.core.utils import normalize_agent_name
from dingent.engine.agents.simple_agent import build_simple_react_agent
from dingent.engine.agents.tools import create_handoff_tool, mcp_tool_wrapper


@asynccontextmanager
async def create_assistant_graphs(
    assistant_factory: AssistantFactory,
    workflow: ExecutableWorkflow,
    llm,
    log_method: Callable,
):
    assistant_graphs = {}

    # 3. 构建每个 Agent 图
    async with AsyncExitStack() as stack:
        for name, assistant_config in workflow.assistant_configs.items():
            rt = await assistant_factory.create_runtime(assistant_config)
            raw_tools = await stack.enter_async_context(rt.load_tools())
            wrapped_tools = [mcp_tool_wrapper(t, log_method) for t in raw_tools]

            # 筛选相关的 Handoff 工具
            destinations = workflow.adjacency_map.get(name, [])
            handoff_tools = [
                create_handoff_tool(normalize_agent_name(dest), description=f"{workflow.assistant_configs[normalize_agent_name(dest)].description}", log_method=log_method)
                for dest in destinations
            ]

            # 构建 Agent
            agent = build_simple_react_agent(
                name=name,
                llm=llm,
                tools=handoff_tools + wrapped_tools,
                system_prompt=None,
            )
            assistant_graphs[name] = agent

        yield assistant_graphs
