import logging
from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager

from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.types import Tool
from pydantic import BaseModel

from .config_manager import get_config_manager
from .plugin_manager import PluginInstance, get_plugin_manager
from .settings import AssistantSettings

config_manager = get_config_manager()
logger = logging.getLogger(__name__)


class RunnableTool(BaseModel):
    tool: Tool
    run: Callable


class Assistant:
    """
    运行期 Assistant。
    destinations: 当前活动 Workflow 中（经 workflow_manager.instantiate_workflow_assistants 构建后）
                  此 Assistant 可直接到达的下游 Assistant ID 列表。
                  单一活动 Workflow 场景下，这里可以直接覆盖。
    """

    name: str
    description: str
    plugin_instances: dict[str, PluginInstance]
    destinations: list[str]

    def __init__(self, name: str, description: str, plugin_instances: dict[str, PluginInstance]):
        self.name = name
        self.description = description
        self.plugin_instances = plugin_instances
        self.destinations = []

    @classmethod
    async def create(cls, settings: AssistantSettings) -> "Assistant":
        plugin_manager = get_plugin_manager()
        plugin_instances = {}
        enabled_plugins = [plugin for plugin in settings.plugins if plugin.enabled]
        for plugin in enabled_plugins:
            plugin_instance = await plugin_manager.create_instance(plugin)
            plugin_instances[plugin.name] = plugin_instance
        return cls(settings.name, settings.description, plugin_instances)

    @asynccontextmanager
    async def load_tools_langgraph(self):
        tools = []
        async with AsyncExitStack() as stack:
            for ins in self.plugin_instances.values():
                client = await stack.enter_async_context(ins.mcp_client)
                session = client.session
                _tools = await load_mcp_tools(session)
                tools.extend(_tools)
            yield tools

    @asynccontextmanager
    async def load_tools(self):
        runnable_tools = []
        async with AsyncExitStack() as stack:
            for ins in self.plugin_instances.values():
                client = await stack.enter_async_context(ins.mcp_client)

                _tools = await client.list_tools()
                for t in _tools:

                    async def call_tool(arguments: dict, _client=client, _tool=t):
                        return await _client.call_tool(_tool.name, arguments=arguments)

                    runnable_tool = RunnableTool(tool=t, run=call_tool)
                    runnable_tools.append(runnable_tool)
            yield runnable_tools

    async def aclose(self):
        for instance in self.plugin_instances.values():
            try:
                await instance.aclose()
            except Exception as e:
                logger.warning("Error closing assistant %s plugin instance: %s", getattr(self, "name", "?"), e)


class AssistantManager:
    """
    仍然缓存已创建的 Assistant 实例。
    _assistants_settings 在初始化时从 config_manager 拿，若配置会动态变化，可在重建时刷新。
    """

    _assistants: dict[str, Assistant]
    _assistants_settings: dict[str, AssistantSettings]

    def __init__(self):
        self._assistants = {}
        self._assistants_settings = config_manager.get_all_assistants_config()

    async def get_assistant(self, id: str) -> Assistant:
        if id in self._assistants:
            return self._assistants[id]
        if id not in self._assistants_settings or not self._assistants_settings[id].enabled:
            raise ValueError(f"Assistant '{id}' not found or is disabled.")
        self._assistants[id] = await Assistant.create(self._assistants_settings[id])
        return self._assistants[id]

    async def get_assistants(self) -> dict[str, Assistant]:
        enabled_ids = [aid for aid, s in self._assistants_settings.items() if s.enabled]
        for aid in enabled_ids:
            if aid not in self._assistants:
                await self.get_assistant(aid)
        return self._assistants

    async def rebuild(self):
        """
        完全重建：关闭所有实例并重新读取配置（适用于配置文件有更新时）。
        """
        await self.aclose()
        self._assistants_settings = config_manager.get_all_assistants_config()

    async def aclose(self):
        for assistant in self._assistants.values():
            try:
                await assistant.aclose()
            except Exception as e:
                logger.warning("Error closing assistant %s: %s", getattr(assistant, "name", "?"), e)
        self._assistants.clear()

    def get_all_assistants_settings(self) -> dict[str, AssistantSettings]:
        """
        给前端调用，返回所有 AssistantSettings（包含禁用的；前端可自行过滤）。
        """
        return config_manager.get_all_assistants_config()

    def refresh_settings_only(self):
        """
        只刷新 settings 引用，不销毁实例（如果你更改了配置但仍想保留现有实例，可调用）。
        """
        self._assistants_settings = config_manager.get_all_assistants_config()


_assistant_manager: AssistantManager | None = None


def get_assistant_manager() -> AssistantManager:
    global _assistant_manager
    if _assistant_manager is None:
        _assistant_manager = AssistantManager()
    return _assistant_manager
