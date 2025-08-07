from dingent.engine.plugins import PluginManager

_plugin_manager = None


def initialize_plugins(**kwargs):
    global _plugin_manager
    _plugin_manager = PluginManager(**kwargs)


def get_plugin_manager() -> None | PluginManager:
    return _plugin_manager
