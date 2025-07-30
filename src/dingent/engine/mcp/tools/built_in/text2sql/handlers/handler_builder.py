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
            must_queried_columns = table.__table__.info.get("must_queried_columns", [])
            modifier = sql_handler.AddColumnsHandler(must_queried_columns, table.__table__.name)
            handlers.append(modifier)
        handlers.append(sql_handler.SQLBuilder())

        return Handler.build_chain(handlers)

    def build_result_chain(self, db: Database) -> Handler:
        """Builds the result processing chain for a given database."""
        sql_run_handler = result_handler.ResultGetHandler(db)

        context_builder = result_handler.ContextBuilder(db)

        pydantic_handler = result_handler.ResultPydanticHandler(db)

        result_to_show = result_handler.ResultToShowHandler(db)

        handlers = [
            sql_run_handler,
            pydantic_handler,
            context_builder,
            result_to_show,
        ]

        return Handler.build_chain(handlers)
