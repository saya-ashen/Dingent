from langchain_core.messages import BaseMessage


class ActivityMessage(BaseMessage):
    type: str = "activity"

    def __init__(self, content: list[dict[str, list[dict]]], **kwargs):
        super().__init__(content=content, **kwargs)
