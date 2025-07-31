from sqlalchemy import inspect

from dingent.engine.mcp.core.db_manager import Database

from . import result_handler, sql_handler
from .base import Handler


class ChainFactory:
    def __init__(
        self,
    ):
        pass

    def build_sql_chain(self, db: Database) -> Handler:
        """Builds the SQL processing chain for a given database."""
        handlers = []

        handlers.append(sql_handler.SQLParser())
        for table in db.tables:
            cte = db.cte
            must_queried_columns:list[str] = table.__table__.info.get("must_queried_columns", [])
            # 添加主键为必须查询的键
            must_queried_columns.extend(inspect(table.__table__).primary_key.columns)
            for column in must_queried_columns:
                if column in cte.conflicting_columns:
                    must_queried_columns.remove(column)
                    must_queried_columns.append(f"{table.__table__.name}_{column}")

            modifier = sql_handler.AddColumnsHandler(must_queried_columns, table.__table__.name)
            handlers.append(modifier)
        handlers.append(sql_handler.SQLBuilder())

        return Handler.build_chain(handlers)

    def build_result_chain(self, db: Database) -> Handler:
        """Builds the result processing chain for a given database."""
        add_cte_handler = sql_handler.SQLAddCTEHandler(db)
        sql_run_handler = result_handler.ResultGetHandler(db)

        context_builder = result_handler.ContextBuilder(db)

        pydantic_handler = result_handler.ResultPydanticHandler(db)

        result_to_show = result_handler.ResultToShowHandler(db)

        handlers = [
            add_cte_handler,
            sql_run_handler,
            pydantic_handler,
            context_builder,
            result_to_show,
        ]

        return Handler.build_chain(handlers)
