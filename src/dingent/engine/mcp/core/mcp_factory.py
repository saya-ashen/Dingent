from typing import Literal

from fastmcp import Context, FastMCP
from loguru import logger

from dingent.engine.shared.llm_manager import LLMManager

from .db_manager import DBManager
from .resource_manager import ResourceManager
from .settings import MCPSettings, get_settings
from .tool_manager import ToolManager

settings = get_settings()


db_manager = DBManager(settings.databases)
llm_manager = LLMManager()
resource_manager = ResourceManager()


async def create_mcp_server(custom_tools_dirs: list, config: MCPSettings, dependencies_override: dict = {}) -> FastMCP:
    """
    创建一个 MCP 服务器实例。

    Args:
        custom_tools_dirs (list): 自定义工具目录列表。
        config (MCPSettings): MCP 服务器的配置。
        dependencies_override (dict): 用于覆盖或添加依赖项的字典。
    """
    mcp = FastMCP(config.name, stateless_http=True, host=config.host, port=config.port)

    # 1. 设置默认依赖项
    main_llm = llm_manager.get_llm(**config.llm)
    db = await db_manager.get_connection(config.database) if config.database else None

    di_container = {
        "db": db,
        "llm": main_llm,
        "resource_manager": resource_manager,
        "vectorstore": None,
        "logger": logger,
    }

    # 2. 应用任何来自 extra_dependencies 的覆盖
    di_container.update(dependencies_override)

    # 3. 使用最终的依赖项创建和加载工具
    tool_manager = ToolManager(di_container)
    tool_manager.load_tools(settings.tools, custom_tools_dirs)

    tools_info = {}
    for enabled_tool in config.enabled_tools:
        for tool_info in settings.tools:
            if tool_info.name == enabled_tool and tool_info.enabled:
                tool_run = tool_manager.load_mcp_tool(tool_info.name)
                mcp.tool(
                    tool_run,
                    name=tool_info.name,
                    description=tool_info.description,
                    exclude_args=tool_info.exclude_args,
                )
                tools_info[tool_info.name] = {
                    "name": tool_info.name,
                    "id": tool_info.name,
                    "description": tool_info.description,
                    "icon": tool_info.icon,
                }

    server_info = {
        "server_name": config.name,
        "server_id": config.name,
        "icon": config.icon,
        "tools_info": tools_info,
        "description": config.description,
    }

    @mcp.resource("info://server_info/{lang}")
    async def get_server_info(ctx: Context, lang: Literal["zh-CN", "en-US"] = "zh-CN"):
        """获取服务器信息"""
        return server_info

    @mcp.resource("resource:tool_output/{resource_id}")
    async def get_tool_output(ctx: Context, resource_id: str):
        resource = resource_manager.get(resource_id)
        return resource

    return mcp


async def create_all_mcp_server(server_names: list[str] = [], extra_dependencies: dict = {}) -> dict[str, 'FastMCP']:
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
    mcp_server_settings = settings.mcp_servers
    all_mcp_servers = {}

    # 提取所有已定义的服务器名称，用于区分全局依赖和特定服务器依赖
    all_defined_server_names = {cfg.name for cfg in mcp_server_settings}
    global_deps = {k: v for k, v in extra_dependencies.items() if k not in all_defined_server_names}

    for mcp_server_config in mcp_server_settings:
        server_name = mcp_server_config.name
        # 如果指定了 server_names，则只创建列表中的服务器
        if server_names and server_name not in server_names:
            continue

        # 组合全局依赖和特定于此服务器的依赖项
        dependencies_for_this_server = global_deps.copy()
        server_specific_deps = extra_dependencies.get(server_name, {})
        dependencies_for_this_server.update(server_specific_deps)

        # 创建 MCP 服务器实例并传入组合后的依赖
        mcp = await create_mcp_server(
            settings.custom_tools_dirs, mcp_server_config, dependencies_override=dependencies_for_this_server
        )
        all_mcp_servers[server_name] = mcp

    return all_mcp_servers
