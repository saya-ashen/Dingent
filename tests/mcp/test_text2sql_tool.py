from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.vectorstores import VectorStore

from dingent.engine.mcp.tools.built_in.text2sql.handlers.base import DBRequest
from dingent.engine.mcp.tools.built_in.text2sql.handlers.sql_handler import *
from dingent.engine.mcp.tools.built_in.text2sql.sql_agent.graph import SQLGeneraterResponse, Text2SqlAgent
from dingent.engine.mcp.tools.built_in.text2sql.tool import Text2SqlTool

pytestmark = pytest.mark.asyncio


class TestSqlProcessingSuite:
    """
    一个测试套件，用于封装所有与 SQL 处理链相关的测试。
    这有助于将相关测试组织在一起，避免污染全局命名空间。
    """

    # --- 1. 单元测试：测试独立的辅助函数 ---

    @pytest.mark.parametrize(
        "sql_in, column, expected_sql",
        [
            ("SELECT * FROM users WHERE name = 'John'", "name", "SELECT * FROM users WHERE name LIKE '%John%'"),
            (
                'SELECT id FROM products WHERE product_name = "Apple"',
                "product_name",
                "SELECT id FROM products WHERE product_name LIKE '%Apple%'",
            ),
            ("SELECT * FROM users WHERE age = 30", "name", "SELECT * FROM users WHERE age = 30"),
            (
                "SELECT * FROM users WHERE name = 'Doe' AND age > 25",
                "name",
                "SELECT * FROM users WHERE name LIKE '%Doe%' AND age > 25",
            ),
        ],
    )
    def test_replace_name_equals_with_like(self, sql_in, column, expected_sql):
        """测试 `replace_name_equals_with_like` 函数"""
        parsed = sqlglot.parse_one(sql_in, dialect="mysql")
        modified_parsed = replace_name_equals_with_like(parsed, column)
        assert modified_parsed.sql(dialect="mysql") == expected_sql

    @pytest.mark.parametrize(
        "sql_in, expected_tables",
        [
            ("SELECT * FROM users", {"users": "users"}),
            ("SELECT * FROM users AS u", {"users": "u"}),
            ("SELECT u.id, p.name FROM users u JOIN posts p ON u.id = p.user_id", {"users": "u", "posts": "p"}),
            ("SELECT 1", {}),
        ],
    )
    def test_get_all_query_tables_and_alias(self, sql_in, expected_tables):
        """测试 `get_all_query_tables_and_alias` 函数"""
        parsed = sqlglot.parse_one(sql_in, dialect="mysql")
        tables = get_all_query_tables_and_alias(parsed)
        assert tables == expected_tables

    @pytest.mark.parametrize(
        "sql_in, column, table, expected_sql",
        [
            ("SELECT id, name FROM users", "created_at", "users", "SELECT id, name, users.created_at FROM users"),
            ("SELECT id FROM users AS u", "created_at", "users", "SELECT id, u.created_at FROM users AS u"),
            ("SELECT id FROM posts", "created_at", "users", "SELECT id FROM posts"),
            ("SELECT id FROM users", "created_at", None, "SELECT id, created_at FROM users"),
            ("SELECT COUNT(*) FROM users", "created_at", "users", "SELECT COUNT(*) FROM users"),
            ("SELECT DISTINCT name FROM users", "created_at", "users", "SELECT DISTINCT name FROM users"),
            ("SELECT * FROM users", "created_at", "users", "SELECT * FROM users"),
        ],
    )
    def test_add_column_sql_conditional(self, sql_in, column, table, expected_sql):
        """测试 `add_column_sql_conditional` 函数"""
        parsed_in = sqlglot.parse_one(sql_in, dialect="mysql")
        modified_parsed = add_column_sql_conditional(parsed_in, column, table)
        expected_parsed = sqlglot.parse_one(expected_sql, dialect="mysql")
        assert str(modified_parsed) == str(expected_parsed)

    # --- 2. 集成测试：测试单个 Handler ---

    async def test_sql_parser_handler(self):
        """测试 SQLParser 是否能正确解析字符串"""
        handler = SQLParser()
        sql_query = "SELECT id FROM my_table"
        request = DBRequest(data={"query": sql_query})

        result_request = await handler.ahandle(request)

        assert isinstance(result_request.data["query"], exp.Expression)
        assert result_request.data["query"].sql() == sql_query

    async def test_add_columns_handler(self):
        """测试 AddColumnsHandler"""
        handler = AddColumnsHandler(columns=["deleted_at", "updated_at"], table="users")
        sql_in = "SELECT id, name FROM users"
        parsed_sql = sqlglot.parse_one(sql_in, dialect="mysql")
        request = DBRequest(data={"query": parsed_sql})

        result_request = await handler.ahandle(request)
        result_sql = result_request.data["query"].sql(dialect="mysql")

        expected_sql = "SELECT id, name, users.deleted_at, users.updated_at FROM users"
        assert result_sql == expected_sql

    async def test_replace_where_handler(self):
        """测试 ReplaceWhereWithLikeHandler"""
        handler = ReplaceWhereWithLikeHandler(columns=["name", "email"])
        sql_in = "SELECT * FROM users WHERE name = 'test' AND email = 'test@a.com' AND age = 10"
        parsed_sql = sqlglot.parse_one(sql_in, dialect="mysql")
        request = DBRequest(data={"query": parsed_sql})

        result_request = await handler.ahandle(request)
        result_sql = result_request.data["query"].sql(dialect="mysql")

        expected_sql = "SELECT * FROM users WHERE name LIKE '%test%' AND email LIKE '%test@a.com%' AND age = 10"
        assert result_sql == expected_sql

    # --- 3. 端到端测试：测试完整的处理链 ---

    async def test_full_chain_integration(self):
        """测试从解析到修改再到构建的完整流程"""
        handlers = [
            SQLParser(),
            AddColumnsHandler(columns=["tenant_id"], table="users"),
            ReplaceWhereWithLikeHandler(columns=["name"]),
            SQLBuilder(),
        ]
        chain_head = Handler.build_chain(handlers)

        sql_in = "SELECT id FROM users WHERE name = 'admin'"
        request = DBRequest(data={"query": sql_in})

        final_request = await chain_head.ahandle(request)
        final_sql = final_request.data["query"]

        expected_sql = "SELECT id, users.tenant_id FROM users WHERE name LIKE '%admin%'"
        assert final_sql == expected_sql


class TestText2SqlAgent:
    """
    Test suite for the Text2SqlAgent, refactored to use Pytest style.
    (Text2SqlAgent 的测试套件，已重构为 Pytest 风格)
    """

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """
        这个 fixture 会在当前类的每个测试运行前自动执行，功能等同于 setUp。
        它将所有 mock 对象和样本数据附加到 `self`，以便在测试方法中访问。
        """
        self.mock_llm = MagicMock()
        self.mock_db = MagicMock()
        cte = MagicMock()
        self.mock_db.cte.return_value = cte
        self.mock_vector_store = MagicMock()
        self.mock_retriever = MagicMock()
        self.mock_sql_statement_handler = MagicMock()
        self.mock_sql_result_handler = MagicMock()
        self.mock_db.cte.return_value = MagicMock()

        self.mock_vector_store.as_retriever.return_value = self.mock_retriever

        # 使用 self 将 agent 实例暴露给测试方法
        self.agent = Text2SqlAgent(
            llm=self.mock_llm,
            db=self.mock_db,
            sql_statement_handler=self.mock_sql_statement_handler,
            sql_result_handler=self.mock_sql_result_handler,
            vectorstore=self.mock_vector_store,
        )

        # 样本数据
        self.SAMPLE_SQL_QUERY = "SELECT * FROM users;"
        self.SAMPLE_DB_RESULT_STR = "user_id: 1, name: 'Alice'"
        self.SAMPLE_DB_RESULT_DICT = {"columns": ["user_id", "name"], "rows": [[1, "Alice"]]}
        self.SUCCESSFUL_HANDLER_RESPONSE = DBRequest(
            data={"str_result": self.SAMPLE_DB_RESULT_STR, "data_to_show": self.SAMPLE_DB_RESULT_DICT}
        )

    # --- 2. 直接使用 `async def` 和 `assert` ---
    @pytest.mark.asyncio
    async def test_successful_run(self):
        """
        测试完整的成功执行流程 (Pytest 版本)。
        """
        # --- Arrange ---
        mock_sql_gen_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": SQLGeneraterResponse.__name__,
                    "args": {"sql_query": self.SAMPLE_SQL_QUERY},
                    "id": "tool_call_123",
                }
            ],
        )
        self.mock_llm.bind_tools.return_value.ainvoke = AsyncMock(return_value=mock_sql_gen_response)
        self.mock_db.get_tables_info.return_value = "Table: users(id, name)"
        self.mock_retriever.invoke.return_value = []
        self.mock_sql_statement_handler.ahandle = AsyncMock(
            return_value=DBRequest(data={"query": self.SAMPLE_SQL_QUERY}, metadata={})
        )
        self.mock_sql_result_handler.ahandle = AsyncMock(return_value=self.SUCCESSFUL_HANDLER_RESPONSE)

        # --- Act ---
        # 直接 await 异步函数，不再需要 _run_async 帮助函数
        _, context, sql_result = await self.agent.arun("Show all users", lang="en-US" )

        # --- Assert ---
        # 使用简单的 assert 语句，更易读
        self.mock_db.get_tables_info.assert_called_once()
        self.mock_retriever.invoke.assert_called_once_with("Show all users")
        self.mock_sql_statement_handler.ahandle.assert_called_once()
        self.mock_sql_result_handler.ahandle.assert_called_once_with(
            DBRequest(data={"query": self.SAMPLE_SQL_QUERY}, metadata={"lang": "en-US"})
        )

        assert sql_result == self.SAMPLE_DB_RESULT_DICT
        assert self.SAMPLE_SQL_QUERY in context
        assert self.SAMPLE_DB_RESULT_STR in context

    @pytest.mark.asyncio
    @patch("dingent.engine.mcp.tools.built_in.text2sql.sql_agent.graph.detect", return_value="zh")
    async def test_run_with_non_english_query(self, mock_detect):
        """
        测试非英语查询的流程 (Pytest 版本)。
        """
        # --- Arrange ---
        translated_query = "Show all users"
        mock_translation_response = AIMessage(content=translated_query)
        mock_sql_gen_response = AIMessage(
            content="",
            tool_calls=[
                {"name": "SQLGeneraterResponse", "args": {"sql_query": self.SAMPLE_SQL_QUERY}, "id": "tool_call_123"}
            ],
        )
        self.mock_llm.ainvoke = AsyncMock(return_value=mock_translation_response)
        self.mock_llm.bind_tools.return_value.ainvoke = AsyncMock(return_value=mock_sql_gen_response)
        self.mock_retriever.invoke.return_value = []
        self.mock_sql_statement_handler.ahandle = AsyncMock(
            return_value=DBRequest(data={"query": self.SAMPLE_SQL_QUERY})
        )
        self.mock_sql_result_handler.ahandle = AsyncMock(return_value=self.SUCCESSFUL_HANDLER_RESPONSE)

        # --- Act ---
        _, context, sql_result = await self.agent.arun("显示所有用户", lang="zh-CN" )

        # --- Assert ---
        self.mock_llm.ainvoke.assert_called_once()
        self.mock_retriever.invoke.assert_called_once_with(translated_query)
        assert sql_result == self.SAMPLE_DB_RESULT_DICT


class TestText2SqlTool:
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_db):
        self.mock_llm = MagicMock(BaseChatModel)
        self.mock_vectorstore = MagicMock(spec=VectorStore)
        retriever = MagicMock()
        retriever.invoke.return_value = []
        self.mock_vectorstore.as_retriever.return_value = retriever
        self.mock_resource_manager = MagicMock()
        cte = MagicMock()
        mock_db.cte.return_value = cte
        self.text2sql_tool = Text2SqlTool(
            db=mock_db,
            llm=self.mock_llm,
            vectorstore=self.mock_vectorstore,
            resource_manager=self.mock_resource_manager,
        )

    @pytest.mark.asyncio
    @patch("dingent.engine.mcp.tools.built_in.text2sql.sql_agent.graph.detect", return_value="en")
    async def test_tool_run(self, mock_detect):
        question = "test"
        mock_responses = [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "args": {
                            "sql_query": "SELECT * FROM overview",
                        },
                        "name": "text2sql",
                        "id": "0",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "args": {
                            "sql_query": "SELECT * FROM overview",
                        },
                        "name": "text2sql",
                        "id": "0",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "args": {
                            "sql_query": "SELECT * FROM overview",
                        },
                        "name": "text2sql",
                        "id": "0",
                    }
                ],
            ),
        ]
        self.mock_llm.ainvoke.side_effect = mock_responses
        self.text2sql_tool.agent.query_gen_chain = self.mock_llm
        result = await self.text2sql_tool.tool_run(question,  "mysql", None)
        self.mock_llm.ainvoke.assert_called_once()
        # FIXME: changed resource to resource id
        # assert result == ""
