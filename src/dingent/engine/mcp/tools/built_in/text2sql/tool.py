from typing import Annotated, Any, Literal

from langchain.chat_models.base import BaseChatModel
from langchain_core.vectorstores import VectorStore
from pydantic import Field

from dingent.engine.mcp import BaseTool, Database
from dingent.engine.mcp.tools.types import TablePayload, ToolOutput

from .graph import Text2SqlAgent
from .handlers.handler_builder import ChainFactory


def format_sql_tool_output(sql_result: dict[str, list[dict[str, Any]]], output_type: Literal["table"] = "table") -> list[ToolOutput]:
    """Formats the raw SQL result into a structured tool output."""
    tool_output = []
    for key, value in sql_result.items():
        columns = list(value[0].keys())
        payload = TablePayload(rows=value, columns=columns, title=key)
        item = ToolOutput(type=output_type, payload=payload)
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
        result_handler = factory.build_result_chain(db)
        self.agent = Text2SqlAgent(
            llm=llm,
            db=db,
            vectorstore=vectorstore,
            sql_result_handler=result_handler,
        )

    async def tool_run(
        self,
        question: Annotated[str, Field(description="sub question of user's original question")],
    ) -> dict:
        """Use the tool."""
        _, context, tool_outputs = await self.agent.arun(user_query=question, recursion_limit=15)
        self.logger.debug(f"SQL tool structured outputs: {tool_outputs}")
        self.logger.debug(f"SQL tool text outputs: {context}")
        tool_outputs = format_sql_tool_output(tool_outputs)

        tool_output_ids = []
        for output in tool_outputs:
            print("register resource", output)
            tool_output_ids.append(self.resource_manager.register(output))

        return {"context": context, "tool_output_ids": tool_output_ids, "source": "text2sql"}
