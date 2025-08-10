from contextlib import asynccontextmanager

from langchain_mcp_adapters.tools import load_mcp_tools

from dingent.engine.plugins.manager import PluginInstance, PluginManager
from dingent.engine.plugins.types import BasePluginUserConfig

from .types import AssistantSettings

plugin_manager = PluginManager()


class Assistant:
    name: str
    description: str
    plugin_instances: list[PluginInstance] = []

    def __init__(self, settings: AssistantSettings):
        self.name = settings.name
        self.description = settings.description
        self.instantize_all_tools(settings.tools)

    def instantize_all_tools(self, tools: list[BasePluginUserConfig]):
        for tool in tools:
            tool_instance = plugin_manager.create_instance(tool)
            self.plugin_instances.append(tool_instance)

    @asynccontextmanager
    async def load_tools_langgraph(self):
        tools = []
        for ins in self.plugin_instances:
            session = ins.mcp_client.session
            _tools = await load_mcp_tools(session)
        yield tools
