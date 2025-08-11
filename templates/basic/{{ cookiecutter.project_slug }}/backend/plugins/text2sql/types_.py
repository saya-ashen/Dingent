from langgraph.graph.message import MessagesState
from pydantic import BaseModel, Field


class Group(BaseModel):
    primary_entity_name: str
    columns: list[str]


class SQLQueryResultPresenter(BaseModel):
    """
    Generates an SQL query and structures its results into a few, intuitive groups for presentation.
    """

    sql_query: str = Field(description="The SQL query that answers the user's question. All calculated or aggregated columns MUST have a clear alias using 'AS'.")

    result_grouping: list[Group] = Field(
        description=(
            "Organize result columns into a minimal number of logical groups.  "
            "A group's title should be an intuitive, human-readable description of its content, not just a raw database table name."
        )
    )


class SQLState(MessagesState):
    """
    Represents the state of the SQL generation graph.

    Attributes:
        sql_result: A list to store the results of the SQL query.
    """

    sql_result: list[dict]
    result_grouping: list[Group] | None
