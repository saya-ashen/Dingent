from ..database import Database
from . import result_handler
from .base import Handler


class ChainFactory:
    def __init__(
        self,
    ):
        pass

    def build_result_chain(self, db: Database) -> Handler:
        """Builds the result processing chain for a given database."""
        sql_run_handler = result_handler.ResultGetHandler(db)

        context_builder = result_handler.ContextBuilder(db)

        pydantic_handler = result_handler.ResultStructureHandler()

        handlers = [
            sql_run_handler,
            pydantic_handler,
            context_builder,
        ]

        return Handler.build_chain(handlers)
