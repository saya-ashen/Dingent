from __future__ import annotations
from typing import Any

from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager


from dingent.core.db.models import Assistant
from dingent.core.schemas import RunnableTool

from .plugin import PluginRuntime
from ..managers.plugin_manager import PluginManager


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
    async def create_runtime(
        cls,
        plugin_manager: PluginManager,
        assistant: Assistant,
        log_method: Callable,
    ) -> AssistantRuntime:
        plugin_instances: dict[str, PluginRuntime] = {}
        enabled_plugins = [p for p in assistant.plugin_links if p.enabled]
        for link in enabled_plugins:
            manifest = link.plugin
            try:
                inst = await plugin_manager.get_or_create_runtime(manifest.registry_id)
                plugin_instances[manifest.registry_id] = inst
            except Exception as e:
                log_method(
                    "error",
                    "Create plugin instance failed (assistant={name} plugin={pid}): {e}",
                    context={"name": assistant.name, "pid": link.plugin_id, "e": e},
                )
                continue
        return cls(str(assistant.id), assistant.name, assistant.description or "", plugin_instances, log_method)

    @asynccontextmanager
    async def load_tools(self):
        """
        返回带可直接运行 run(arguments) 的 RunnableTool 列表。
        """
        runnable: list[RunnableTool] = []
        for inst in self.plugin_instances.values():
            # 先短暂进入上下文列出工具，避免长时间持有连接。
            async with inst.mcp_client as client:
                tools = await client.list_tools()

            for t in tools:

                async def call_tool(arguments: dict, _runtime=inst, _tool=t):
                    async with _runtime.mcp_client as tool_client:
                        return await tool_client.call_tool(_tool.name, arguments=arguments)

                runnable.append(RunnableTool(tool=t, run=call_tool))
        yield runnable

    @asynccontextmanager
    async def _load_tools(self):
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
