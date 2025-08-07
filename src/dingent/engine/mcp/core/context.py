from dingent.engine.plugins import PluginManager

plugin_manager = None


def initialize_plugins(**kwargs):
    global plugin_manager
    plugin_manager = PluginManager(**kwargs)
