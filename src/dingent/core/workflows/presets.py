import uuid

from dingent.core.schemas import AssistantSpec, NodeSpec, ExecutableWorkflow


def get_fallback_workflow_spec() -> ExecutableWorkflow:
    """
    返回默认的兜底 Workflow Spec。
    通常是一个简单的单节点对话。
    """
    default_assistant = AssistantSpec(
        name="DefaultAssistant",
        description="A default assistant",
        plugins=[],
    )
    # default_node = NodeSpec(is_start_node=True, assistant=default_assistant)

    return ExecutableWorkflow(
        id=uuid.uuid4(),
        name="DefaultAgent",
        start_node="DefaultAssistant",
        assistant_configs={"DefaultAssistant": default_assistant},
        adjacency_map={},
    )
