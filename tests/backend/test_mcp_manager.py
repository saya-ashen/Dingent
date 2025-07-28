import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client

from backend.core.settings import MCPServerInfo
from backend.core.mcp_manager import AsyncMCPManager, get_async_mcp_manager


# 2. 测试类
class TestAsyncMCPManager:
    """针对 AsyncMCPManager 的测试套件。"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_server_configs = [
            MCPServerInfo(name="server1", host="127.0.0.1", port=9001),
            MCPServerInfo(name="server2", host="127.0.0.1", port=9002),
        ]

    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试管理器是否使用提供的配置正确初始化。"""
        manager = AsyncMCPManager(self.mock_server_configs)

        # 验证内部配置是否按预期格式化
        expected_configs = {
            "server1": {"transport": "http://127.0.0.1:9001/mcp"},
            "server2": {"transport": "http://127.0.0.1:9002/mcp"},
        }

        assert manager._server_configs == expected_configs
        assert manager._connection_timeout == 5.0
        assert not manager._active_clients  # 初始时应为空
        assert not manager._client_managers  # 初始时应为空

    @pytest.mark.asyncio
    @patch("backend.core.mcp_manager.Client")  # 模拟 fastmcp.Client
    async def test_aenter_successful_connection(self, MockClient):
        """测试上下文进入时能否成功连接所有客户端。"""

        # 模拟 __aenter__ 返回一个可用的客户端对象
        mock_active_client = AsyncMock(spec=Client)
        mock_client_manager = MockClient.return_value
        mock_client_manager.__aenter__.return_value = mock_active_client

        manager = AsyncMCPManager(server_configs=self.mock_server_configs)

        async with manager as m:
            # 验证返回的实例是其自身
            assert m is manager
            # 验证所有服务器都已连接
            assert len(m.active_clients) == len(self.mock_server_configs)
            assert "server1" in m.active_clients
            assert "server2" in m.active_clients
            assert m.get_client("server1") is mock_active_client

            # 验证 list_tools 被调用以验证连接
            mock_active_client.list_tools.assert_awaited()

    @pytest.mark.asyncio
    @patch("backend.core.mcp_manager.Client")
    async def test_aenter_connection_failure(self, MockClient, capsys):
        """测试当部分客户端连接失败时的处理情况。"""

        # 配置模拟：第一个成功，第二个失败
        mock_ok_client = AsyncMock(spec=Client)

        def client_side_effect(*args, **kwargs):
            transport = kwargs.get("transport", "")
            if "9002" in transport:  # 模拟 server2 连接失败
                manager = AsyncMock()
                manager.__aenter__.side_effect = asyncio.TimeoutError("Connection timed out")
                return manager
            else:  # 模拟 server1 连接成功
                manager = AsyncMock()
                manager.__aenter__.return_value = mock_ok_client
                return manager

        MockClient.side_effect = client_side_effect

        manager = AsyncMCPManager(server_configs=self.mock_server_configs, connection_timeout=0.1)

        async with manager as m:
            # 验证只有一个客户端处于活动状态
            assert len(m.active_clients) == 1
            assert "server1" in m.active_clients
            assert "server2" not in m.active_clients

            # 检查失败日志是否被打印
            captured = capsys.readouterr()
            assert "连接到 'server2' (http://127.0.0.1:9002/mcp) 失败" in captured.out

    @pytest.mark.asyncio
    @patch("backend.core.mcp_manager.Client")
    async def test_aexit_cleans_up_resources(self, MockClient):
        """测试上下文退出时是否正确清理所有资源。"""
        mock_client_manager = MockClient.return_value
        mock_client_manager.__aenter__.return_value = AsyncMock(spec=Client)

        manager = AsyncMCPManager(server_configs=self.mock_server_configs)

        async with manager:
            assert len(manager.active_clients) == 2
            assert len(manager._client_managers) == 2

        # 验证退出后，所有内部状态都被清空
        assert not manager.active_clients
        assert not manager._client_managers

        # 验证所有客户端管理器的 __aexit__ 方法都被调用了
        assert mock_client_manager.__aexit__.call_count == len(self.mock_server_configs)

    @pytest.mark.asyncio
    async def test_get_client(self):
        """测试 get_client 方法的行为。"""
        manager = AsyncMCPManager(self.mock_server_configs)

        # 在进入上下文之前，应该返回 None
        assert manager.get_client("server1") is None

        mock_client = MagicMock()
        manager._active_clients["server1"] = mock_client

        # 模拟进入上下文后
        assert manager.get_client("server1") is mock_client
        assert manager.get_client("non_existent_server") is None

    def test_active_clients_property(self):
        """测试 active_clients 属性返回的是一个副本。"""
        manager = AsyncMCPManager(self.mock_server_configs)
        manager._active_clients["server1"] = MagicMock()

        clients_copy = manager.active_clients
        assert "server1" in clients_copy

        # 修改副本不应影响原始字典
        clients_copy["new_server"] = MagicMock()
        assert "new_server" not in manager._active_clients

    def test_get_async_mcp_manager(self):
        """测试 get_async_mcp_manager 工厂函数。"""
        timeout = 10.0
        log_handler = MagicMock()

        manager = get_async_mcp_manager(
            server_configs=self.mock_server_configs,
            connection_timeout=timeout,
            log_handler=log_handler,
        )

        # 验证它是否返回了一个正确配置的 AsyncMCPManager 实例
        assert isinstance(manager, AsyncMCPManager)
        assert manager._connection_timeout == timeout
        assert manager._log_handler is log_handler
        assert len(manager._server_configs) == len(self.mock_server_configs)
