from langgraph_swarm import SwarmState


# 基础 Swarm 状态
class MainState(SwarmState):
    a2ui_action: dict


SimpleAgentState = MainState

# class SimpleAgentState(CopilotKitState, total=False):
#     # 使用 add reducer，这也是为什么 tools_node 必须返回增量的原因
#     messages: Annotated[list[BaseMessage], operator.add]
#     iteration: int
#     a2uiAction: dict
