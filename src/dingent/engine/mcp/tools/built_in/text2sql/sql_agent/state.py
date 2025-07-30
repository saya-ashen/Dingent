from langgraph.graph.message import MessagesState
from typing import List
from danticsql import CteGenerationResult


class SQLState(MessagesState):
    """
    Represents the state of the SQL generation graph.

    Attributes:
        sql_result: A list to store the results of the SQL query.
    """

    sql_result: List[dict]
    cte:  CteGenerationResult| None
