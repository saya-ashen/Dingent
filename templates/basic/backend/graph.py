import uuid

from copilotkit import CopilotKitState
from langchain_core.messages import AIMessage, ToolCall
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.types import Command


class MainState(CopilotKitState):
    events: list = []


def call_actions(state, list_of_args: list):
    actions = state.get("copilotkit", {}).get("actions", [])
    show_data_action = None
    for action in actions:
        if action["name"] =="show_data":
            show_data_action = action
    if show_data_action is None:
        raise ValueError("No action named 'show_data' found in the state.")
    action_call_messages = []
    for args in list_of_args:
        tool_call = ToolCall(
            name="show_data",
            args=args,
            id=f"tool_{uuid.uuid4()}",  # 生成一个唯一的 ID
        )
        action_call_messages.append(AIMessage(content="", tool_calls=[tool_call]))
    return action_call_messages


async def chat_node(state: MainState, config: RunnableConfig):
    messages = call_actions(
        state,
        [
            {
                "type":"table",
                "metadata":{"showType":"card"},
                "payload": {
                    "headers": ["test1", "test2"],
                    "rows": [
                        {"test1": 1, "test2": 2},
                        {"test1": 1, "test2": 2},
                        {"test1": 1, "test2": 2},
                        {"test1": 1, "test2": 2},
                        {"test1": 1, "test2": 2},
                    ],
                },
            },
             {
                "type":"markdown",
                "payload": {
                    "content": "# abc \n\n [](www.baidu.com)"
                    ,
                },
            }
        ],
    )
    state["messages"].extend(messages)
    print(messages)
    return Command(goto=END, update={"messages": state["messages"]})



workflow = StateGraph(MainState)
workflow.add_node("chat_node", chat_node)
workflow.add_edge("chat_node", END)
workflow.set_entry_point("chat_node")
graph = workflow.compile()
