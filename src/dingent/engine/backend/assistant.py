from contextlib import AsyncExitStack, asynccontextmanager

from langchain_mcp_adapters.tools import load_mcp_tools

from dingent.engine.plugins.manager import PluginInstance, get_plugin_manager

from .settings import AssistantSettings, settings


class Assistant:
    name: str
    description: str
    plugin_instances: list[PluginInstance] = []

    def __init__(self, name, description, plugin_instances):
        self.name = name
        self.description = description
        self.plugin_instances = plugin_instances

    @classmethod
    async def create(cls, settings: AssistantSettings) -> "Assistant":
        plugin_manager = get_plugin_manager()
        plugin_instances = []
        enabled_plugins = [plugin for plugin in settings.plugins if plugin.enabled]
        for plugin in enabled_plugins:
            plugin_instance = await plugin_manager.create_instance(plugin)
            plugin_instances.append(plugin_instance)
        return cls(settings.name, settings.description, plugin_instances)

    @asynccontextmanager
    async def load_tools_langgraph(self):
        tools = []
        async with AsyncExitStack() as stack:
            for ins in self.plugin_instances:
                client = await stack.enter_async_context(ins.mcp_client)
                session = client.session
                _tools = await load_mcp_tools(session)
                tools.extend(_tools)
            yield tools


class AssistantManager:
    _assistants: dict[str, Assistant] = {}
    _assistants_settings: dict[str, AssistantSettings] = {}

    def __init__(self):
        self._assistants_settings = {settings.name: settings for settings in settings.assistants}

    def list_assistants(self) -> dict[str, AssistantSettings]:
        return self._assistants_settings

    async def get_assistant(self, name):
        if name in self._assistants:
            return self._assistants[name]
        else:
            if name not in self._assistants_settings or not self._assistants_settings[name].enabled:
                raise ValueError(f"Assistant '{name}' not found or is disabled.")
            self._assistants[name] = await Assistant.create(self._assistants_settings[name])
            return self._assistants[name]

    async def get_assistants(self):
        enabled_assistants = [name for name, settings in self._assistants_settings.items() if settings.enabled]
        for name in enabled_assistants:
            if name not in self._assistants:
                await self.get_assistant(name)
        return self._assistants


_assistant_manager = None


def get_assistant_manager() -> AssistantManager:
    global _assistant_manager
    if _assistant_manager is None:
        _assistant_manager = AssistantManager()
    return _assistant_manager
