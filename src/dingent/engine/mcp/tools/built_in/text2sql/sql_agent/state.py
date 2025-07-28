from langgraph.graph.message import MessagesState
from typing import List


class SQLState(MessagesState):
    """
    Represents the state of the SQL generation graph.

    Attributes:
        sql_result: A list to store the results of the SQL query.
    """

    sql_result: List[dict]
