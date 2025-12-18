from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict


class ActivityMessage(BaseMessage):
    type: str = "activity"

    def __init__(self, content: list[dict[str, list[dict]]], **kwargs):
        super().__init__(content=content, **kwargs)
