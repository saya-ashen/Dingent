import asyncio
from collections.abc import Callable

from fastmcp import Client

from dingent.engine.backend.core.settings import MCPServerInfo


class AsyncMCPManager:
    """
    一个基于 asyncio 的管理器，用于高效地管理与多个 MCP 服务器的客户端连接。
    它使用异步上下文协议 (async with) 来自动处理连接和断开。
    """

    def __init__(
        self,
        server_configs: list[MCPServerInfo],
        connection_timeout: float = 5.0,
        log_handler: Callable | None = None,
    ):
        """
        初始化管理器。

        Args:
            server_configs (Dict[str, str]): 一个字典，键是服务器的唯一名称，值是传输地址 (e.g., "tcp://127.0.0.1:9001")。
            connection_timeout (float): 每个客户端的连接超时时间。
            log_handler (Optional[logging.Handler]): 用于客户端日志的处理器。
        """
        self._server_configs = {}
        for config in server_configs:
            self._server_configs[config.name] = {"transport": f"http://{config.host}:{config.port}/mcp"}
        self._connection_timeout = connection_timeout
        self._log_handler = log_handler

        # 内部状态：存储上下文管理器实例和活动客户端实例
        self._client_managers: dict[str, Client] = {}
        self._active_clients: dict[str, Client] = {}

    async def __aenter__(self):
        """
        进入异步上下文，并发地连接到所有配置的服务器。
        """
        print("--- [管理器] 进入上下文，正在并发连接所有客户端... ---")

        async def _connect_one(name: str, transport: str):
            """尝试连接单个客户端，并处理成功或失败。"""
            try:
                # 1. 创建客户端上下文管理器实例
                manager = Client(transport=transport, log_handler=self._log_handler)
                self._client_managers[name] = manager

                # 2. 手动进入其上下文以获取活动的客户端对象
                client = await asyncio.wait_for(manager.__aenter__(), timeout=self._connection_timeout)

                # 3. 发送一个简单的请求来验证连接是否真的可用
                await client.list_tools()

                # 4. 如果成功，存储活动的客户端
                self._active_clients[name] = client
                print(f"✅ [管理器] 成功连接到 '{name}' ({transport})")

            except Exception as e:
                print(f"❌ [管理器] 连接到 '{name}' ({transport}) 失败: {e}")
                # 如果连接失败，确保它不在活动客户端列表中
                if name in self._active_clients:
                    del self._active_clients[name]
                # manager可能已创建，但会在__aexit__中被安全地处理

        # 并发执行所有连接任务
        connection_tasks = [_connect_one(name, config["transport"]) for name, config in self._server_configs.items()]
        await asyncio.gather(*connection_tasks)

        print(
            f"--- [管理器] 连接过程完成。{len(self._active_clients)} / {len(self._server_configs)} 个客户端已激活。---"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        退出异步上下文，并发地断开所有已连接的客户端。
        """
        print("\n--- [管理器] 退出上下文，正在断开所有客户端连接... ---")

        # 并发地对所有创建的管理器实例调用 __aexit__
        # 这会安全地关闭那些成功连接的客户端
        cleanup_tasks = [manager.__aexit__(exc_type, exc_val, exc_tb) for manager in self._client_managers.values()]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)  # return_exceptions 确保一个失败不会中断其他

        self._active_clients.clear()
        self._client_managers.clear()
        print("--- [管理器] 所有客户端已断开。---")

    def get_client(self, server_name: str) -> Client | None:
        """
        获取一个已激活的客户端实例。

        Args:
            server_name (str): 服务器的唯一名称。

        Returns:
            Optional[MCPClient]: 如果客户端已激活则返回实例，否则返回 None。
        """
        return self._active_clients.get(server_name)

    @property
    def active_clients(self) -> dict[str, Client]:
        """返回所有活动客户端的字典。"""
        return self._active_clients.copy()


def get_async_mcp_manager(
    server_configs: list[MCPServerInfo],
    connection_timeout: float = 5.0,
    log_handler: Callable | None = None,
) -> AsyncMCPManager:
    """
    获取一个缓存的异步 MCP 管理器实例。

    Args:
        server_configs (Dict[str, Dict[str, str]]): 服务器配置字典。
        connection_timeout (float): 每个客户端的连接超时时间。
        log_handler (Optional[Callable]): 用于客户端日志的处理器。

    Returns:
        AsyncMCPManager: 管理器实例。
    """
    return AsyncMCPManager(server_configs, connection_timeout, log_handler)
