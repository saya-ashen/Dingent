import pandas as pd
import pytest
from sqlmodel import SQLModel

from dingent.engine.mcp.core.db_manager import Database


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
