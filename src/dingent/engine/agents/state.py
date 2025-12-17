import operator
from typing import Annotated, TypedDict

from copilotkit import CopilotKitState
from langchain_core.messages import BaseMessage
from langgraph_swarm import SwarmState


# 基础 Swarm 状态
class MainState(CopilotKitState, SwarmState):
    artifact_ids: list[str]


# 单个 Agent 的子图状态
class SimpleAgentState(TypedDict, total=False):
    # 使用 add reducer，这也是为什么 tools_node 必须返回增量的原因
    messages: Annotated[list[BaseMessage], operator.add]
    iteration: int
    artifact_ids: list[str]
