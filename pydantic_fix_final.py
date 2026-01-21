from pydantic import BaseModel, ConfigDict, Field
from typing import List, Union, Literal, Annotated, Optional


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(x.capitalize() for x in parts[1:])


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        alias_generator=to_camel,
        populate_by_name=True,
    )


class AGUIAssistantMessage(ConfiguredBaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class UserMessage(ConfiguredBaseModel):
    role: Literal["user"] = "user"
    content: str


class MessagesSnapshotEvent(ConfiguredBaseModel):
    # 原始定义
    messages: List[Annotated[Union[AGUIAssistantMessage, UserMessage], Field(discriminator="role")]]


# --- 你的扩展 ---


class DingAGUIAssistantMessage(AGUIAssistantMessage):
    thinking_content: str | None = None


# 【正确方案】重新定义 Union，替换掉冲突的父类
MyCustomMessageUnion = Annotated[
    Union[
        DingAGUIAssistantMessage,  # 替换了 AGUIAssistantMessage
        UserMessage,
    ],
    Field(discriminator="role"),
]


class DingMessagesSnapshotEvent(MessagesSnapshotEvent):
    # 完全覆盖 messages 类型
    messages: List[MyCustomMessageUnion]


if __name__ == "__main__":
    msg = DingAGUIAssistantMessage(content="Hello", thinking_content="I am thinking...")
    event = DingMessagesSnapshotEvent(messages=[msg])

    print(event.model_dump_json())
