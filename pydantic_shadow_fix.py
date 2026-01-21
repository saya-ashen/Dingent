from pydantic import BaseModel, ConfigDict, Field
from typing import List, Union, Literal, Annotated, Optional


# 1. 模拟库中的定义 (Library Logic)
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


# 库定义的联合类型 (注意这里包含了 AGUIAssistantMessage)
AGUIMessage = Annotated[Union[AGUIAssistantMessage, UserMessage], Field(discriminator="role")]


class MessagesSnapshotEvent(ConfiguredBaseModel):
    messages: List[AGUIMessage]


# 2. 你的扩展定义 (Your Logic)
class DingAGUIAssistantMessage(AGUIAssistantMessage):
    thinking_content: str | None = None


# 【问题代码复现】
class BuggyEvent(MessagesSnapshotEvent):
    # 这里 AGUIMessage 在前，它包含了父类 AGUIAssistantMessage
    # Pydantic 可能会优先匹配到父类 schema，从而忽略子类字段
    messages: List[Union[AGUIMessage, DingAGUIAssistantMessage]]


# 【修复代码】
class FixedEvent(MessagesSnapshotEvent):
    # 策略：明确把你的子类放在最前面
    messages: List[Union[DingAGUIAssistantMessage, AGUIMessage]]


# 3. 运行测试
if __name__ == "__main__":
    msg = DingAGUIAssistantMessage(content="Hello", thinking_content="Deep thought...")

    print("--- Buggy Event Dump ---")
    buggy = BuggyEvent(messages=[msg])
    # 预期：missing thinkingContent
    print(buggy.model_dump_json())

    print("\n--- Fixed Event Dump ---")
    fixed = FixedEvent(messages=[msg])
    # 预期：includes thinkingContent
    print(fixed.model_dump_json())
