from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from fastmcp import Context
from langchain.chat_models.base import BaseChatModel
from langchain_chroma import Chroma
from sqlmodel import SQLModel

from mcp_servers.core.db_manager import Database
from mcp_servers.core.language_manager import LanguageManager
from mcp_servers.tools.built_in.text2sql.handlers.base import Handler

# 为了让代码可独立运行，我们在这里创建假的基类


@pytest.fixture
def mock_llm():
    """模拟 LLM"""
    llm = MagicMock(spec=BaseChatModel)
    llm.ainvoke = AsyncMock()
    # 模拟工具调用返回的结构
    mock_ai_message = MagicMock()
    mock_ai_message.tool_calls = [{"args": {"sql_query": "SELECT * FROM mock_table;"}}]
    llm.ainvoke.return_value = mock_ai_message
    return llm


@pytest.fixture
def mock_vector_store():
    """模拟向量存储"""
    retriever = MagicMock()
    retriever.invoke.return_value = []  # 返回空的文档列表

    store = MagicMock(spec=Chroma)
    store.as_retriever.return_value = retriever
    return store


@pytest.fixture
def mock_language_manager():
    """模拟语言管理器"""
    manager = MagicMock(spec=LanguageManager)
    manager.get_translator.return_value = lambda s: s  # 返回一个什么都不做的翻译函数
    return manager


@pytest.fixture
def mock_sql_statement_handler():
    """模拟 SQL 语句处理器"""
    handler = MagicMock(spec=Handler)
    # 默认情况下，处理器返回它接收到的查询
    handler.ahandle = AsyncMock(side_effect=lambda req: req)
    return handler


@pytest.fixture
def mock_sql_result_handler():
    """模拟 SQL 结果处理器"""
    handler = MagicMock(spec=Handler)
    mock_result = {
        "data": {
            "data_to_show": {"mock_table": {"rows": [[1, "A"]], "columns": ["id", "name"]}},
            "str_result": "Query returned 1 row: [1, 'A']",
        }
    }
    handler.ahandle = AsyncMock(return_value=mock_result)
    return handler


@pytest.fixture
def mock_context():
    """模拟上下文对象"""
    return MagicMock(spec=Context)


@pytest.fixture
def mock_get_stream_writer(mocker):
    """模拟 get_stream_writer 函数"""
    # 阻止测试期间的任何实际写入操作
    return mocker.patch("langgraph.config.get_stream_writer", return_value=MagicMock())


class MockDatabase(Database):
    """
    一个专用于测试的 Database 替身。
    它继承自 Database，因此可以复用 `get_tables_info` 和 `_describe` 的逻辑，
    但覆盖了 `__init__` 和 `run` 等方法以避免与真实数据库和文件系统交互。
    """

    def __init__(self, mock_tables: list[type[SQLModel]]):
        """
        覆盖原始的 __init__ 方法。
        我们不调用 super().__init__()，以避免数据库连接和文件读取。
        我们直接设置 `_tables` 属性。
        """
        print("++ Calling MOCK Database __init__ (SAFE FOR TESTS)")
        self._tables = mock_tables
        self.db = None  # 确保没有数据库引擎
        self.summarizer = None  # 也可以按需模拟这个

    def run(self, query: str) -> dict:
        """
        覆盖原始的 run 方法。
        返回一个预设的、假的 DataFrame。
        """
        print(f"++ Calling MOCK Database run with query: '{query}' (SAFE FOR TESTS)")
        fake_df = pd.DataFrame(
            [
                {"disease_name": "Cancer", "biomarker_name": "BRCA1"},
                {"disease_name": "Diabetes", "biomarker_name": "Glucose"},
            ]
        )
        return {"data": fake_df, "metadata": {"query": query, "source": "mock"}}

    def read_all(self) -> dict:
        """
        覆盖原始的 read_all 方法。
        返回一个假的、预设的字典。
        """
        print("++ Calling MOCK Database read_all (SAFE FOR TESTS)")
        return {"overview": ["{'disease_name': 'Cancer', 'biomarker_name': 'BRCA1'}"]}


@pytest.fixture
def mock_db():
    """模拟上下文对象"""
    return MockDatabase([])
