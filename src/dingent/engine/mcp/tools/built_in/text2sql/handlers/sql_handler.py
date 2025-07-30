import sqlglot
from typing import Type
from sqlglot import exp
from danticsql import generate_cte_with_mapping
from sqlmodel import SQLModel

from .base import Handler


def replace_name_equals_with_like(parsed, column):
    # 遍历 AST 并找到所有 WHERE 条件中的 name = <value>
    for condition in parsed.find_all(exp.EQ):
        if isinstance(condition.left, exp.Column) and condition.left.name == column:
            # 获取当前条件的值
            value = condition.right.this.strip('"')
            # 替换为不区分大小写的 LIKE 语句
            condition.replace(
                exp.Like(
                    this=exp.Column(this=condition.left),
                    expression=exp.Literal(this=f"%{value}%", is_string=True),
                )
            )
    # 生成修改后的 SQL 语句
    return parsed


def get_all_query_tables_and_alias(parsed):
    """
    return: {table_name: alias or table_name if alias is None}
    """
    for select in parsed.find_all(exp.Select):
        # 使用字典来存储表名和别名
        tables = {}
        for from_ in select.find_all(exp.From):
            if isinstance(from_.this, exp.Table):
                table_name = from_.this.name
                alias = from_.this.alias_or_name
                tables[table_name] = alias
        for join in select.find_all(exp.Join):
            if isinstance(join.this, exp.Table):
                table_name = join.this.name
                alias = join.this.alias_or_name
                tables[table_name] = alias
        return tables
    return {}


def add_column_sql(parsed, column_name: str):
    if isinstance(parsed, exp.Select):
        # 检查是否存在聚合函数
        has_aggregate = any(
            isinstance(select, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)) for select in parsed.selects
        )

        # 检查是否存在 DISTINCT
        has_distinct = parsed.args.get("distinct") is not None

        # 检查是否存在 HAVING
        has_having = parsed.args.get("having") is not None

        # 检查是否存在 GROUP BY
        has_group_by = parsed.args.get("group") is not None

        # 如果存在聚合函数、DISTINCT、HAVING 或 GROUP BY，不修改
        if has_aggregate or has_distinct or has_having or has_group_by:
            return parsed

        select_all = any(isinstance(select, exp.Star) for select in parsed.selects)
        has_added = any(
            isinstance(select, exp.Column) and select.name == column_name.split(".")[-1] for select in parsed.selects
        )
        if not select_all and not has_added:
            parsed = parsed.select(column_name, append=True)
    return parsed


def add_column_sql_conditional(parsed, column_name: str, table: str | None):
    if table is not None:
        tables = get_all_query_tables_and_alias(parsed)
        if table in tables.keys():
            return add_column_sql(parsed, f"{tables[table]}.{column_name}")
        else:
            return parsed
    else:
        return add_column_sql(parsed, column_name)


class SchemaMismatchError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class SQLAddCTEHandler(Handler):
    def __init__(self):
        super().__init__()

    async def ahandle(self, request):
        raw_query = request.data["query"]
        cte = request.data["cte"]
        query = f"""
        {cte.sql_string}
        {raw_query}
        """
        request.data["query"] = query
        request.data["raw_query"] = raw_query
        return await self._apass_to_next(request)

class SQLParser(Handler):
    async def ahandle(self, request):
        query = request.data["query"]
        assert isinstance(query, str)
        parsed_sql = sqlglot.parse_one(query, dialect="mysql")
        request.data["query"] = parsed_sql
        return await self._apass_to_next(request)


class SQLBuilder(Handler):
    async def ahandle(self, request):
        query = request.data["query"]
        request.data["query"] = query.sql()
        return await self._apass_to_next(request)


class ReplaceWhereWithLikeHandler(Handler):
    def __init__(self, columns: list[str]):
        super().__init__()
        self.columns = columns

    async def ahandle(self, request):
        query = request.data["query"]
        for column in self.columns:
            query = replace_name_equals_with_like(query, column)
        request.data["query"] = query
        return await self._apass_to_next(request)


class AddColumnsHandler(Handler):
    def __init__(self, columns: list[str], table: str | None = None):
        super().__init__()
        self.columns = columns
        self.table = table

    async def ahandle(self, request):
        query = request.data["query"]
        for column in self.columns:
            query = add_column_sql_conditional(query, column, self.table)
        request.data["query"] = query
        return await self._apass_to_next(request)
