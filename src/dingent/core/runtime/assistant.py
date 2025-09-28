from __future__ import annotations
from typing import Any
from mcp.types import Tool

from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager

from langchain_mcp_adapters.tools import load_mcp_tools
from pydantic import BaseModel

from dingent.core.db.models import Assistant

from .plugin import PluginRuntime
from ..plugin_manager import PluginManager


class RunnableTool(BaseModel):
    tool: Tool
    run: Callable[[dict], Any]


class AssistantRuntime:
    """
    运行期 Assistant。
    destinations: 当前活动 Workflow 中（经 workflow_manager.instantiate_workflow_assistants 构建后）
                  此 Assistant 可直接到达的下游 Assistant 名称（或 ID）列表。
                  单一活动 Workflow 场景下，可以直接覆盖。
    """

    def __init__(
        self,
        assistant_id: str,
        name: str,
        description: str,
        plugin_instances: dict[str, PluginRuntime],
        log_method: Callable,
    ):
        self.id = assistant_id
        self.name = name
        self.description = description
        self.plugin_instances = plugin_instances
        self.destinations: list[str] = []
        self._log_method = log_method

    @classmethod
    async def create(
        cls,
        plugin_manager: PluginManager,
        assistant: Assistant,
        log_method: Callable,
    ) -> AssistantRuntime:
        plugin_instances: dict[str, PluginRuntime] = {}
        enabled_plugins = [p for p in assistant.plugin_links if p.enabled]
        for link in enabled_plugins:
            try:
                inst = await plugin_manager.create_instance(link)
                plugin_instances[str(link.plugin_id)] = inst
            except Exception as e:
                log_method(
                    "error",
                    "Create plugin instance failed (assistant={name} plugin={pid}): {e}",
                    context={"name": assistant.name, "pid": link.plugin_id, "e": e},
                )
                continue
        return cls(str(assistant.id), assistant.name, assistant.description or "", plugin_instances, log_method)

    @asynccontextmanager
    async def load_tools_langgraph(self):
        """
        返回 langgraph 期望的 tool 列表（普通 Tool 对象）。
        """
        tools: list = []
        async with AsyncExitStack() as stack:
            for inst in self.plugin_instances.values():
                client = await stack.enter_async_context(inst.mcp_client)
                session = client.session
                _tools = await load_mcp_tools(session)
                tools.extend(_tools)
            yield tools

    @asynccontextmanager
    async def load_tools(self):
        """
        返回带可直接运行 run(arguments) 的 RunnableTool 列表。
        """
        runnable: list[RunnableTool] = []
        async with AsyncExitStack() as stack:
            for inst in self.plugin_instances.values():
                client = await stack.enter_async_context(inst.mcp_client)
                tools = await client.list_tools()
                for t in tools:

                    async def call_tool(arguments: dict, _client=client, _t=t):
                        return await _client.call_tool(_t.name, arguments=arguments)

                    runnable.append(RunnableTool(tool=t, run=call_tool))
            yield runnable

    async def aclose(self):
        for inst in self.plugin_instances.values():
            try:
                await inst.aclose()
            except Exception as e:
                self._log_method("warning", "Error closing plugin instance (assistant={name}): {e}", context={"name": self.name, "e": e})
        self.plugin_instances.clear()
