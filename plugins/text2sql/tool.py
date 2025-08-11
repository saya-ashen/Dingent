from typing import Annotated

from fastmcp import FastMCP
from langchain.chat_models import init_chat_model
from pydantic import Field

from dingent.engine.backend.types import TablePayload

from .database import Database
from .graph import Text2SqlAgent
from .handlers.handler_builder import ChainFactory
from .settings import Settings

try:
    settings = Settings()
except Exception as e:
    raise RuntimeError("Failed to load Text2SQL settings. Please check your configuration.") from e

mcp = FastMCP()


def format_sql_tool_output(sql_result: dict[str, list[dict[str, any]]]):
    """Formats the raw SQL result into a structured tool output."""
    payloads = []
    for key, value in sql_result.items():
        columns = list(value[0].keys())
        payload = TablePayload(rows=value, columns=columns, title=key)
        payloads.append(payload)
    return {"payloads": payloads}


class Text2SqlTool:
    """A tool that uses the Text2SqlAgent to answer questions from a database."""

    agent: Text2SqlAgent

    def __init__(
        self,
        settings: Settings,
        **kwargs,
    ):
        super().__init__(**kwargs)
        db = Database(**settings.database.model_dump())
        factory = ChainFactory()
        result_handler = factory.build_result_chain(db)
        llm = init_chat_model(**settings.llm)
        self.agent = Text2SqlAgent(
            llm=llm,
            db=db,
            sql_result_handler=result_handler,
        )

    async def tool_run(
        self,
        question: Annotated[str, Field(description="sub question of user's original question")],
    ) -> dict:
        """Use the tool."""
        _, context, tool_outputs = await self.agent.arun(user_query=question, recursion_limit=15)
        tool_outputs = format_sql_tool_output(tool_outputs)

        return {"context": context, "tool_outputs": tool_outputs}


tool = Text2SqlTool(settings)
mcp.tool(tool.tool_run)
if __name__ == "__main__":
    mcp.run()
