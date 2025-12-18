import uuid

from dingent.core.schemas import AssistantSpec, NodeSpec, WorkflowSpec


def get_fallback_workflow_spec() -> WorkflowSpec:
    """
    返回默认的兜底 Workflow Spec。
    通常是一个简单的单节点对话。
    """
    default_assistant = AssistantSpec(
        name="DefaultAssistant",
        description="A default assistant",
        version="1.0",
        spec_version="1.0",
        plugins=[],
        enabled=True,
    )
    default_node = NodeSpec(is_start_node=True, assistant=default_assistant)

    return WorkflowSpec(
        id=uuid.uuid4(),
        name="DefaultAgent",
        start_node_name="DefaultAssistant",
        nodes=[default_node],
    )
