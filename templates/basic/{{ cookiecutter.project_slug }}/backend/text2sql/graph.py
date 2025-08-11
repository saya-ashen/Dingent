from collections import defaultdict
from typing import Any, Literal, cast

from langchain.chat_models.base import BaseChatModel
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langdetect import detect
from langgraph.graph import END, StateGraph
from loguru import logger

from .database import Database
from .handlers.base import DBRequest, Handler
from .types_ import SQLQueryResultPresenter, SQLState

COMMON_SQL_GEN_PROMPT = """
You are an expert {dialect} data analyst. Your sole task is to generate a single, efficient SQL query in response to a user's question, based on the provided database schema.

### Instructions:
1.  **Primary Goal**: Write a syntactically correct and efficient {dialect} query that accurately answers the user's question.
2.  **Query Constraints**:
    - The generated query MUST only contain English characters.
    - **Do not use the `DISTINCT` keyword.** The calling application handles deduplication.
    - Whenever you query columns from a table, you MUST also include its primary key in the SELECT list. This is crucial for subsequent processing.
    - You may order the results by the most relevant columns to provide a more meaningful output.
3.  **Output Format**: Your entire response must be ONLY the SQL query. Do not include any explanations, comments, or other conversational text.

### Database Schema:
{tables_info}
"""
TRANSLATOR_PROMPT = """# Role: Text-to-SQL Keyword Extractor and Translator

## Profile:
You are an expert assistant specializing in Natural Language Processing (NLP) and database query generation.
Your primary function is to analyze user questions formulated in Chinese, identify key terms crucial for constructing SQL queries, and then translate these terms into English.
The translated keywords will be used for Retrieval Augmented Generation (RAG) to fetch relevant database schema information or similar query patterns.

## Task:
Given a user's question in Chinese, perform the following steps:
1.  **Identify Keywords:** Carefully read the user's question and extract the most relevant keywords.
2.  **Translate Keywords:** Translate each identified Chinese keyword into its most appropriate and concise English equivalent.

## Constraints:
* Focus solely on terms that are directly relevant to forming a SQL query.
* Avoid extracting stop words or general conversational phrases.

Avoid adding any additional details or explanations in the response. Output only the translated keywords in English, separated by commas.

## User's Question:
{question}
"""


class Text2SqlAgent:
    """An agent that converts natural language to SQL queries and executes them."""

    def __init__(
        self,
        llm: BaseChatModel,
        db: Database,
        sql_result_handler: Handler,
        vectorstore=None,
    ):
        self.llm = llm
        self.db = db
        if vectorstore:
            self.retriever = vectorstore.as_retriever(search_kwargs={"k": 50})
        else:
            self.retriever = None
        self.sql_result_handler = sql_result_handler
        self.graph = self._build_graph()
        if self.retriever:
            prompt_template = COMMON_SQL_GEN_PROMPT + "\n\n### Contextual Examples (for reference only):\n{similar_rows}"
        else:
            prompt_template = COMMON_SQL_GEN_PROMPT
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_template),
                ("placeholder", "{messages}"),
            ]
        )

        self.query_gen_chain = prompt | self.llm.with_structured_output(SQLQueryResultPresenter)

    def _build_graph(self):
        """Builds the LangGraph agent."""
        workflow = StateGraph(SQLState)

        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_sql", self._execute_sql)

        workflow.set_entry_point("generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_conditional_edges("execute_sql", self._should_retry)

        return workflow.compile()

    def _should_retry(self, state: SQLState) -> Literal["generate_sql", END]:
        """Determines whether to retry SQL generation after an execution error."""
        last_message = state["messages"][-1]
        # If the last message is a HumanMessage starting with "Error:", it indicates a failure.
        if isinstance(last_message, HumanMessage) and last_message.content.startswith("Error:"):
            return "generate_sql"
        return END

    async def _similarity_search(self, query: str) -> str:
        """Performs similarity search to find relevant schema/data examples."""
        if detect(query) != "en":
            translation_prompt = TRANSLATOR_PROMPT.format(question=query)
            translated_message = await self.llm.ainvoke(translation_prompt)
            query = cast(str, translated_message.content)

        assert self.retriever is not None
        docs = self.retriever.invoke(query)
        columns_data = defaultdict(list)
        for doc in docs:
            columns_data[doc.metadata["column"]].append(doc.page_content)

        text = ""
        for column, values in columns_data.items():
            text += f"{column}: {','.join(values[:5])}\n"
        return text

    async def _generate_sql(self, state: SQLState, config: RunnableConfig) -> dict[str, Any]:
        """Generates the SQL query from the user question."""
        dialect = config.get("configurable", {}).get("dialect", "mysql")

        user_query = cast(str, state["messages"][-1].content)
        tables_info = self.db.get_tables_info()
        if not tables_info:
            toolkit = SQLDatabaseToolkit(db=SQLDatabase(self.db.db), llm=self.llm)
            tools = toolkit.get_tools()
            sql_db_list_tables = None
            sql_db_schema = None
            for tool in tools:
                if tool.name == "sql_db_schema":
                    sql_db_schema = tool
                elif tool.name == "sql_db_list_tables":
                    sql_db_list_tables = tool
            assert sql_db_list_tables is not None and sql_db_schema is not None, "SQL Database tools are not available."
            tables = sql_db_list_tables.run("")
            tables_info = sql_db_schema.run(tables)

        tables_info = str(tables_info)

        logger.debug(f"Generating SQL for user query: {user_query}; Tables info: {tables_info}")
        if self.retriever:
            similar_rows = await self._similarity_search(user_query)
        else:
            similar_rows = ""

        response = await self.query_gen_chain.ainvoke(
            {
                "messages": state["messages"],
                "tables_info": tables_info,
                "similar_rows": similar_rows,
                "dialect": dialect,
            }
        )
        response = cast(SQLQueryResultPresenter, response)

        sql_query = response.sql_query

        if not sql_query:
            raise ValueError("LLM failed to generate a SQL query.")

        return {"messages": [AIMessage(content=sql_query, role="ai")], "result_grouping": response.result_grouping}

    async def _execute_sql(self, state: SQLState, config: RunnableConfig) -> dict[str, Any]:
        """Executes the SQL query against the database."""
        sql_query = str(state["messages"][-1].content)
        result_grouping = state.get("result_grouping")
        request: DBRequest = DBRequest(data={"query": sql_query, "result_grouping": result_grouping})

        try:
            response = await self.sql_result_handler.ahandle(request)

            # Message for the next step (summarization or end)
            tool_message = HumanMessage(content=response.data["str_result"], name="db_query_tool")

            return {
                "messages": [tool_message],
                "sql_result": response.data.get("result", {}),
            }

        except Exception as e:
            logger.warning(f"Error executing SQL query: {e}. Rewriting")
            error_message = HumanMessage(content=f"Error: Query failed. Please rewrite your query and try again. Error information: {e}")
            return {"messages": [error_message]}

    async def arun(
        self,
        user_query: str,
        recursion_limit: int = 15,
    ) -> tuple[str | None, str, dict]:
        """Runs the complete text-to-SQL process."""
        dialect = self.db.dialect
        config = {"recursion_limit": recursion_limit, "configurable": {"dialect": dialect}}
        initial_state = {"messages": [HumanMessage(content=user_query)]}

        final_state = {}
        query = ""
        sql_result = {}
        text_result = ""

        async for chunk in self.graph.astream(initial_state, config=config, stream_mode="updates"):
            # Process streaming output for logging or real-time updates
            if "generate_sql" in chunk:
                # The AIMessage with the SQL query
                query = chunk["generate_sql"]["messages"][-1].content
            if "execute_sql" in chunk:
                final_state = chunk["execute_sql"]
                sql_result = final_state.get("sql_result", {})
                text_result = final_state["messages"][-1].content

        context = f"=== Generated SQL Query ===\n{query}\n\n=== SQL Result ===\n{text_result}\n\n"
        return None, context, sql_result
