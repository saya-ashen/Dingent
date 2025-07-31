from typing import Annotated, Literal

from langchain.chat_models.base import BaseChatModel
from langchain_core.vectorstores import VectorStore
from pydantic import Field

from dingent.engine.mcp import BaseTool, Database, ToolOutput

from .handlers.handler_builder import ChainFactory
from .sql_agent.graph import Text2SqlAgent


def format_sql_tool_output(sql_result: dict[str, dict], output_type: Literal["table"] = "table") -> list[ToolOutput]:
    """Formats the raw SQL result into a structured tool output."""
    tool_output = []
    for key, value in sql_result.items():
        columns = list(value["rows"][0].keys())
        item = {"type": output_type, "payload": {"rows": value["rows"], "columns": columns, "title": key}}
        tool_output.append(item)
    return tool_output


class Text2SqlTool(BaseTool):
    """A tool that uses the Text2SqlAgent to answer questions from a database."""

    agent: Text2SqlAgent

    def __init__(
        self,
        db: Database,
        llm: BaseChatModel,
        vectorstore: VectorStore,
        **kwargs,
    ):
        super().__init__(**kwargs)
        factory = ChainFactory()
        sql_handler = factory.build_sql_chain(db)
        result_handler = factory.build_result_chain(db)
        self.agent = Text2SqlAgent(
            llm=llm,
            db=db,
            vectorstore=vectorstore,
            sql_statement_handler=sql_handler,
            sql_result_handler=result_handler,
        )

    async def tool_run(
        self,
        question: Annotated[str, Field(description="sub question of user's original question")],
        lang: Literal["en-US", "zh-CN"] = "en-US",
        tool_output=None,
    ) -> dict:
        """Use the tool."""
        _, context, sql_result = await self.agent.arun(
            user_query=question,recursion_limit=15
        )
        self.logger.info(f"SQL Result: {sql_result}")
        tool_outputs = format_sql_tool_output(sql_result)
        tool_output_ids = []

        for output in tool_outputs:
            self.logger.info(f"register resource: {output}")
            tool_output_ids.append(self.resource_manager.register(output))

        return {"context": context, "tool_output_ids": tool_output_ids, "source": "text2sql"}
