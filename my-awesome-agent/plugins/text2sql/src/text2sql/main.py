import os
from typing import Annotated, Any

from fastmcp import FastMCP
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from .database import Database
from .graph import Text2SqlAgent
from .handlers.handler_builder import ChainFactory

mcp = FastMCP()

config = {
    "db_uri": os.getenv("DB_URI"),
    "db_name": os.getenv("DB_NAME"),
    "dialect": os.getenv("DB_DIALECT"),
    "schemas_path": os.getenv("SCHEMAS_PATH"),
    "llm": {
        "model": os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo"),
        "model_provider": os.getenv("LLM_PROVIDER", "openai"),
        "api_key": os.getenv("LLM_API_KEY"),
        "base_url": os.getenv("LLM_BASE_URL"),
    },
}


class Settings(BaseModel):
    db_uri: str
    db_name: str
    db_dialect: str | None = "mysql"
    schemas_path: str | None = None
    llm: dict


settings = Settings.model_validate(config)


def format_sql_tool_output(sql_result: dict[str, list[dict[str, Any]]]):
    """Formats the raw SQL result into a structured tool output."""
    payloads = []
    for key, value in sql_result.items():
        columns = list(value[0].keys())
        # payload = {"rows": value, "columns": columns, "title": key}
        payload = {"type":"table","columns":columns, "rows":value, "title":key}
        payloads.append(payload)
    return payloads


class Text2SqlTool:
    """A tool that uses the Text2SqlAgent to answer questions from a database."""

    agent: Text2SqlAgent

    def __init__(
        self,
        settings: Settings,
        **kwargs,
    ):
        super().__init__(**kwargs)
        db = Database(uri=settings.db_uri, name=settings.db_name, dialect=settings.db_dialect, schemas_path=settings.schemas_path)
        factory = ChainFactory()
        result_handler = factory.build_result_chain(db)
        llm = init_chat_model(**settings.llm)
        self.agent = Text2SqlAgent(
            llm=llm,
            db=db,
            sql_result_handler=result_handler,
        )

    async def text2sql(
        self,
        question: Annotated[str, Field(description="sub question of user's original question")],
    ) -> dict:
        """Answers a question using the Text2SqlAgent."""
        _, context, tool_outputs = await self.agent.arun(user_query=question, recursion_limit=15)
        tool_outputs = format_sql_tool_output(tool_outputs)

        return {"model_text": context, "display": tool_outputs}


tool = Text2SqlTool(settings)
mcp.tool(tool.text2sql)
if __name__ == "__main__":
    mcp.run()
