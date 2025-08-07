from fastmcp import FastMCP

from dingent.engine.plugins import PluginManager
from dingent.engine.shared.llm_manager import LLMManager

from .resource_manager import ResourceManager
from .settings import AssistantSettings, get_settings

settings = get_settings()


llm_manager = LLMManager()
resource_manager = ResourceManager()
global_injection_deps = {"resource_manager": resource_manager}
plugin_manager = PluginManager(global_injection_deps=global_injection_deps)


async def create_assistant(config: AssistantSettings, injection_deps: dict) -> FastMCP:
    """
    Creates an MCP server instance.

    Args:
        config (MCPSettings): The configuration for the MCP server.
        dependencies_override (dict): A dictionary to override or add dependencies.
    """
    mcp = FastMCP(config.name, stateless_http=True, host=config.host, port=config.port)
    deps = global_injection_deps.update(injection_deps)

    tools = config.tools
    tools_info = {}
    for tool in tools:
        if not tool.enabled:
            continue
        tool_instance = plugin_manager.load_plugin(tool.type_name, {"name": tool.name, "description": tool.description, **deps})
        tool_run = tool_instance.tool_run
        mcp.tool(
            tool_run,
            name=tool.name,
            description=tool_instance.description,
            exclude_args=tool_instance.exclude_args,
        )
        tools_info[tool.name] = {
            "name": tool.name,
            "id": tool.name,
            "description": tool.description,
        }

    server_info = {
        "server_name": config.name,
        "server_id": config.name,
        "icon": config.icon,
        "tools_info": tools_info,
        "description": config.description,
    }

    @mcp.resource("info://server_info/en-US")
    async def get_server_info():
        """Get server information"""
        return server_info

    @mcp.resource("resource:tool_output/{resource_id}")
    async def get_tool_output(resource_id: str):
        """Get the output of a tool resource"""
        resource = resource_manager.get(resource_id)
        return resource

    return mcp


async def create_all_assistants(assistant_names: list[str] | None = None, extra_dependencies: dict | None = None) -> dict[str, "FastMCP"]:
    """
    Creates all MCP server instances.

    Args:
        server_names (list[str]): An optional list of server names. If provided, only servers
                                  with these names will be created.
        extra_dependencies (dict): An optional dictionary for extra dependencies.
                                   Supported formats:
                                   - Global dependency: {"db": db_instance} will be passed to all servers.
                                   - Server-specific dependency: {"server_name_1": {"llm": llm_instance}} will only be passed to `server_name_1`.
    """
    assistants_settings = settings.assistants
    all_assistants = {}
    if extra_dependencies is None:
        extra_dependencies = {}

    # Extract all defined server names to distinguish between global and server-specific dependencies
    all_defined_server_names = {cfg.name for cfg in assistants_settings}
    global_deps = {k: v for k, v in extra_dependencies.items() if k not in all_defined_server_names}

    for assistant_settings in assistants_settings:
        server_name = assistant_settings.name
        # If server_names is provided, only create the servers in the list
        if assistant_names and server_name not in assistant_names:
            continue

        # Combine global dependencies and dependencies specific to this server
        dependencies_for_this_server = global_deps.copy()
        server_specific_deps = extra_dependencies.get(server_name, {})
        dependencies_for_this_server.update(server_specific_deps)

        # Create the MCP server instance and pass in the combined dependencies
        mcp = await create_assistant(assistant_settings, injection_deps=dependencies_for_this_server)
        all_assistants[server_name] = mcp

    return all_assistants
