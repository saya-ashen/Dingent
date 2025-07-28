from typing import Annotated, Literal

from fastmcp import Context
from langchain.chat_models.base import BaseChatModel
from langchain_core.vectorstores import VectorStore
from pandas import DataFrame
from pydantic import Field

from dingent.engine.mcp import BaseTool, Database, ResourceManager, ToolOutput

from .handlers.handler_builder import ChainFactory
from .sql_agent.graph import Text2SqlAgent


def format_sql_tool_output(sql_result: dict|DataFrame, output_type: Literal["table"] = "table")->list[ToolOutput]:
    """Formats the raw SQL result into a structured tool output."""
    if isinstance(sql_result,dict):
        tool_output = []
        for key, value in sql_result.items():
            columns = list(value["rows"][0].keys())
            item = {"type": output_type, "payload": {"rows": value["rows"], "columns": columns}}
            tool_output.append(item)
        return tool_output
    elif isinstance(sql_result,DataFrame):
        data = sql_result.to_dict(orient='split')
        return [{"type": output_type, "payload": {"rows": data["rows"], "columns": data["columns"]}}]



class Text2SqlTool(BaseTool):
    """A tool that uses the Text2SqlAgent to answer questions from a database."""

    agent: Text2SqlAgent

    def __init__(
        self,
        db: Database,
        llm: BaseChatModel,
        language_manager,
        vectorstore: VectorStore,
        resource_manager:ResourceManager,
    ):
        super().__init__()
        # Handlers are now created and passed during agent initialization
        factory = ChainFactory()
        sql_handler = factory.build_sql_chain(db)
        result_handler = factory.build_result_chain(db)
        self.agent = Text2SqlAgent(
            llm=llm,
            db=db,
            vectorstore=vectorstore,
            language_manager=language_manager,
            sql_statement_handler=sql_handler,
            sql_result_handler=result_handler,
        )
        self.resource_manager = resource_manager
        assert resource_manager is not None

    async def tool_run(
        self,
        question: Annotated[str, Field(description="sub question of user's original question")],
        lang: Literal["en-US", "zh-CN"] = "en-US",
        dialect: Literal["mysql", "postgresql"] = "mysql",
        tool_output = None,
        ctx: Context | None = None,
    ) -> dict:
        """Use the tool."""
        _, context, sql_result = await self.agent.arun(
            user_query=question, lang=lang, ctx=ctx, dialect=dialect, recursion_limit=15
        )
        tool_outputs = format_sql_tool_output(sql_result)
        tool_output_ids = []
        for output in tool_outputs:
            print("register resource",output)
            tool_output_ids.append(self.resource_manager.register(output))

        return {"context": context, "tool_output_ids": tool_output_ids, "source": "bioka.text2sql"}
