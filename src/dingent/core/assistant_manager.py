import logging
from contextlib import AsyncExitStack, asynccontextmanager

from langchain_mcp_adapters.tools import load_mcp_tools

from .config_manager import get_config_manager
from .plugin_manager import PluginInstance, get_plugin_manager
from .settings import AssistantSettings

config_manager = get_config_manager()


logger = logging.getLogger(__name__)

class Assistant:
    name: str
    description: str
    plugin_instances: dict[str, PluginInstance] = {}

    def __init__(self, name, description, plugin_instances):
        self.name = name
        self.description = description
        self.plugin_instances = plugin_instances

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

    async def aclose(self):
        for instance in self.plugin_instances.values():
            await instance.aclose()


class AssistantManager:
    _assistants: dict[str, Assistant] = {}
    _assistants_settings: dict[str, AssistantSettings] = {}

    def __init__(self):
        self._assistants_settings = config_manager.get_all_assistants_config()

    async def get_assistant(self, id: str):
        if id in self._assistants:
            return self._assistants[id]
        else:
            if id not in self._assistants_settings or not self._assistants_settings[id].enabled:
                raise ValueError(f"Assistant '{id}' not found or is disabled.")
            self._assistants[id] = await Assistant.create(self._assistants_settings[id])
            return self._assistants[id]

    async def get_assistants(self):
        enabled_assistants = [id for id, settings in self._assistants_settings.items() if settings.enabled]
        for id in enabled_assistants:
            if id not in self._assistants:
                await self.get_assistant(id)
        return self._assistants

    async def rebuild(self):
        await self.aclose()
        self._assistants_settings = config_manager.get_all_assistants_config()
        self._assistants.clear()

    async def aclose(self):
        for assistant in self._assistants.values():
            try:
                await assistant.aclose()
            except Exception as e:
                logger.warning("Error closing assistant %s: %s", getattr(assistant, "name", "?"), e)
        self._assistants.clear()


_assistant_manager = None


def get_assistant_manager() -> AssistantManager:
    global _assistant_manager
    if _assistant_manager is None:
        _assistant_manager = AssistantManager()
    return _assistant_manager
