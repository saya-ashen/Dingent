import json
from typing import AsyncGenerator, cast
import uuid

from ag_ui.core import ActivityMessage, EventType, MessagesSnapshotEvent, RunAgentInput
from ag_ui.core.events import RunStartedEvent
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from ag_ui_langgraph.agent import langchain_messages_to_agui
from ag_ui_langgraph.utils import (
    AGUIAssistantMessage,
    AGUIFunctionCall,
    AGUIMessage,
    AGUISystemMessage,
    AGUIToolCall,
    AGUIToolMessage,
    AGUIUserMessage,
    convert_langchain_multimodal_to_agui,
    resolve_message_content,
    stringify_if_needed,
)
from copilotkit import LangGraphAGUIAgent


class DingRunAgentInput(RunAgentInput):
    owner_id: uuid.UUID


def ding_langchain_messages_to_agui(messages: list[BaseMessage]):
    agui_messages: list[AGUIMessage] = []
    for message in messages:
        if isinstance(message, ToolMessage):
            agui_messages.append(
                AGUIToolMessage(
                    id=str(message.id),
                    role="tool",
                    content=stringify_if_needed(resolve_message_content(message.content)),
                    tool_call_id=message.tool_call_id,
                )
            )
            if message.artifact:
                agui_messages.append(
                    ActivityMessage(
                        activity_type="a2ui-surface",
                        id=str(uuid.uuid4()),
                        content=message.artifact,
                    )
                )
        elif isinstance(message, HumanMessage):
            # Handle multimodal content
            if isinstance(message.content, list):
                content = convert_langchain_multimodal_to_agui(message.content)
            else:
                content = stringify_if_needed(resolve_message_content(message.content))

            agui_messages.append(
                AGUIUserMessage(
                    id=str(message.id),
                    role="user",
                    content=content,
                    name=message.name,
                )
            )
        elif isinstance(message, AIMessage):
            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    AGUIToolCall(
                        id=str(tc["id"]),
                        type="function",
                        function=AGUIFunctionCall(
                            name=tc["name"],
                            arguments=json.dumps(tc.get("args", {})),
                        ),
                    )
                    for tc in message.tool_calls
                ]

            agui_messages.append(
                AGUIAssistantMessage(
                    id=str(message.id),
                    role="assistant",
                    content=stringify_if_needed(resolve_message_content(message.content)),
                    tool_calls=tool_calls,
                    name=message.name,
                )
            )
        elif isinstance(message, SystemMessage):
            agui_messages.append(
                AGUISystemMessage(
                    id=str(message.id),
                    role="system",
                    content=stringify_if_needed(resolve_message_content(message.content)),
                    name=message.name,
                )
            )
        else:
            raise TypeError(f"Unsupported message type: {type(message)}")
    return agui_messages


import ag_ui_langgraph

ag_ui_langgraph.agent.langchain_messages_to_agui = ding_langchain_messages_to_agui


class DingLangGraphAGUIAgent(LangGraphAGUIAgent):
    """
    自定义 Agent 类
    """

    async def run(self, input: RunAgentInput, extra_config: dict | None = None) -> AsyncGenerator[str, None]:
        # 1. 备份当前的 config
        # 我们只保存引用即可，因为后续我们是赋值新的字典给 self.config，而不是原地修改
        previous_config = self.config

        # 2. 合并配置 (Extend self.config)
        # 确保 current_config 是一个字典，即使 previous_config 是 None
        current_config = previous_config.copy() if previous_config else {}

        if extra_config:
            # 将传入的 extra_config 合并到当前配置中
            # 注意：extra_config 中的键值对会覆盖原有的配置
            current_config.update(extra_config)

        # 更新实例的 config
        self.config = current_config

        try:
            # 3. 调用父类的 run 方法
            # 由于父类 run 是一个 AsyncGenerator，我们需要遍历它并 yield 出来
            async for event_str in super().run(input):
                yield event_str
        finally:
            # 4. 恢复原来的 config
            # 无论上面的代码是否报错，这里都会执行，确保状态回滚
            self.config = previous_config

    async def get_thread_messages(self, thread_id: str, run_id: str):
        """
        [新增功能] 根据 thread_id 获取该对话的所有历史消息。
        返回格式已转换为前端友好的 AG-UI 格式。
        """

        config = self.graph.config or {}
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["thread_id"] = thread_id

        state = await self.graph.aget_state(config)

        # 提取 messages
        messages = state.values.get("messages", [])

        yield self._dispatch_event(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=thread_id,
                run_id=run_id,
            )
        )
        yield self._dispatch_event(
            MessagesSnapshotEvent(type=EventType.MESSAGES_SNAPSHOT, messages=langchain_messages_to_agui(messages)),
        )
