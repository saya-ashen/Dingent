import asyncio
from collections.abc import Callable

from fastmcp import Client
from loguru import logger

from dingent.engine.backend.core.settings import MCPServerInfo


class AsyncMCPManager:
    """
    An asyncio-based manager for efficiently handling client connections to multiple MCP servers.
    It uses the async context protocol (async with) to automatically handle connections and disconnections.
    """

    def __init__(
        self,
        server_configs: list[MCPServerInfo],
        connection_timeout: float = 5.0,
        log_handler: Callable | None = None,
    ):
        """
        Initializes the manager.

        Args:
            server_configs (list[MCPServerInfo]): A list of server configuration objects.
            connection_timeout (float): The connection timeout for each client.
            log_handler (Optional[logging.Handler]): A handler for client logging.
        """
        self._server_configs = {}
        for config in server_configs:
            self._server_configs[config.name] = {"transport": f"http://{config.host}:{config.port}/mcp"}
        self._connection_timeout = connection_timeout
        self._log_handler = log_handler

        # Internal state: stores client manager instances and active client instances
        self._client_managers: dict[str, Client] = {}
        self._active_clients: dict[str, Client] = {}

    async def __aenter__(self):
        """
        Enters the async context, concurrently connecting to all configured servers.
        """
        logger.info("--- [Manager] Entering context, connecting all clients concurrently... ---")

        async def _connect_one(name: str, transport: str):
            """Tries to connect a single client and handles success or failure."""
            try:
                # 1. Create a client context manager instance
                manager = Client(transport=transport, log_handler=self._log_handler)
                self._client_managers[name] = manager

                # 2. Manually enter its context to get the active client object
                client = await asyncio.wait_for(manager.__aenter__(), timeout=self._connection_timeout)

                # 3. Send a simple request to verify the connection is truly alive
                await client.list_tools()

                # 4. If successful, store the active client
                self._active_clients[name] = client
                logger.info(f"✅ [Manager] Successfully connected to '{name}' ({transport})")

            except Exception as e:
                logger.error(f"❌ [Manager] Failed to connect to '{name}' ({transport}): {e}")
                # If the connection fails, ensure it's not in the list of active clients
                if name in self._active_clients:
                    del self._active_clients[name]
                # The manager might have been created, but it will be handled safely in __aexit__.

        # Concurrently execute all connection tasks
        connection_tasks = [_connect_one(name, config["transport"]) for name, config in self._server_configs.items()]
        await asyncio.gather(*connection_tasks)

        logger.info(f"--- [Manager] Connection process finished. {len(self._active_clients)} / {len(self._server_configs)} clients are active. ---")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the async context, concurrently disconnecting all connected clients.
        """
        logger.info("\n--- [Manager] Exiting context, disconnecting all client connections... ---")

        # Concurrently call __aexit__ on all created manager instances.
        # This safely closes the clients that were successfully connected.
        cleanup_tasks = [manager.__aexit__(exc_type, exc_val, exc_tb) for manager in self._client_managers.values()]
        # return_exceptions ensures one failure doesn't interrupt others.
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._active_clients.clear()
        self._client_managers.clear()
        logger.info("--- [Manager] All clients have been disconnected. ---")

    def get_client(self, server_name: str) -> Client | None:
        """
        Gets an active client instance.

        Args:
            server_name (str): The unique name of the server.

        Returns:
            Optional[Client]: The client instance if active, otherwise None.
        """
        return self._active_clients.get(server_name)

    @property
    def active_clients(self) -> dict[str, Client]:
        """Returns a dictionary of all active clients."""
        return self._active_clients.copy()


def get_async_mcp_manager(
    server_configs: list[MCPServerInfo],
    connection_timeout: float = 5.0,
    log_handler: Callable | None = None,
) -> AsyncMCPManager:
    """
    Factory function to get an AsyncMCPManager instance.

    Args:
        server_configs (list[MCPServerInfo]): A list of server configuration objects.
        connection_timeout (float): The connection timeout for each client.
        log_handler (Optional[Callable]): A handler for client logging.

    Returns:
        AsyncMCPManager: The manager instance.
    """
    return AsyncMCPManager(server_configs, connection_timeout, log_handler)
