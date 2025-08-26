"""
提供用于测试的 Dummy / Fake 环境实体。
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

# 尝试使用官方 FakeListChatModel
from langchain.chat_models.base import init_chat_model
from langchain_core.tools import StructuredTool, tool

# ---------------------------
# Dummy Config / Workflow
# ---------------------------


@dataclass
class DummyLLMConfig:
    model_provider: str = "fake"
    model_name: str = "fake-small"

    def model_dump(self):
        return {
            "model_provider": self.model_provider,
            "model_name": self.model_name,
        }


@dataclass
class DummyConfig:
    llm: DummyLLMConfig = field(default_factory=DummyLLMConfig)


@dataclass
class DummyNodeData:
    assistantName: str
    isStart: bool = False


@dataclass
class DummyNode:
    data: DummyNodeData


@dataclass
class DummyWorkflow:
    id: str
    nodes: list[DummyNode]


# ---------------------------
# Dummy Assistant
# ---------------------------


class DummyAssistant:
    def __init__(self, name: str, description: str, tools: list[StructuredTool], destinations: list[str] | None = None):
        self.name = name
        self.description = description
        self._tools = tools
        self.destinations = destinations or []

    @asynccontextmanager
    async def load_tools_langgraph(self):
        # 产出一个工具列表
        yield self._tools


# ---------------------------
# Dummy Managers
# ---------------------------


class DummyLLMManager:
    def get_llm(self, **kwargs):
        # 如果你想用真实模型，可在这里替换，比如返回 ChatOpenAI(...)
        return init_chat_model(
            model="gpt-5",
            model_provider="openai",
            base_url="https://www.dmxapi.cn/v1",
            api_key="sk-mx79KrgdiE7LAshJy6Qc4EzPCrxf36zLk1YGpx4t24GaMrLb",
        )


class DummyConfigManager:
    def __init__(self, workflow: DummyWorkflow, config: DummyConfig):
        self._workflow = workflow
        self._config = config

    def get_config(self):
        return self._config

    def get_current_workflow(self):
        return self._workflow


class DummyWorkflowManager:
    def __init__(self, assistants: dict[str, DummyAssistant]):
        self._assistants = assistants

    async def instantiate_workflow_assistants(self, workflow_id: str, reset_assistants: bool = False):
        # 返回 {id: assistant} 结构
        # 为方便直接用 assistant.name 作为 key
        return {a.name: a for a in self._assistants.values()}


# ---------------------------
# Example Tools
# ---------------------------


@tool
def get_weather(city: str) -> str:
    """
    天气工具，返回 JSON 格式
    """
    fake_weather = {"city": city, "temp_c": 26, "condition": "Sunny"}
    payload = {"context": f"Weather for {city}: {fake_weather['temp_c']}C, {fake_weather['condition']}", "tool_output_id": str(uuid.uuid4()), "raw": fake_weather}
    return json.dumps(payload, ensure_ascii=False)


@tool
def get_time(zone: str) -> str:
    """
    时间查询
    """
    return f"Zone {zone} time: 2025-08-26T09:00:00"


def build_dummy_assistants():
    a1 = DummyAssistant(
        name="WeatherAgent",
        description="专门回答天气问题",
        tools=[get_weather],
        destinations=["TimeAgent"],
    )
    # 你可以添加第二个 Agent 测试 handoff
    a2 = DummyAssistant(
        name="TimeAgent",
        description="时间服务",
        tools=[get_time],
        destinations=[],  # 可以转回
    )
    return {a1.name: a1, a2.name: a2}
