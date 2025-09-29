from typing import Optional

from dingent.core.runtime.plugin import PluginRuntime
from dingent.core.schemas import AssistantRead, PluginRead

from ..db.models import Assistant, AssistantPluginLink
from ..runtime.assistant import AssistantRuntime


def _build_plugin_read(plugin_link: AssistantPluginLink, runtime_plugin: Optional[PluginRuntime]) -> PluginRead:
    """
    辅助函数：从数据库和运行时模型构建单个 PluginRead DTO。
    """
    plugin_db = plugin_link.plugin

    plugin_status = "inactive"
    if runtime_plugin:
        plugin_status = runtime_plugin.status  # "active", "error", etc.

    return PluginRead(
        id=str(plugin_db.id),
        display_name=plugin_db.display_name,
        description=plugin_db.description,
        enabled=plugin_link.enabled,  # 用户在此 Assistant 中的启用状态
        status=plugin_status,
        version=plugin_db.version,
    )


def _build_assistant_read(assistant: Assistant, runtime_assistant: Optional[AssistantRuntime]) -> AssistantRead:
    """
    主映射函数：从 Assistant 的持久化模型和运行时模型构建 AssistantRead DTO。
    """
    # 校验输入的一致性
    if runtime_assistant:
        assert str(assistant.id) == runtime_assistant.id, "Mismatched Assistant and AssistantRuntime IDs"

    # 确定顶层状态
    assistant_status = "active" if runtime_assistant else "inactive"

    # 可以在这里加入更复杂的逻辑，例如检查runtime_assistant内部的错误状态
    # if runtime_assistant and runtime_assistant.has_error:
    #     assistant_status = "error"

    # 递归构建嵌套的 plugins 列表
    plugins_read_list: list[PluginRead] = []
    for plugin_link in assistant.plugin_links:
        runtime_plugin = None
        if runtime_assistant:
            # 从运行时实例中通过 ID 找到对应的插件实例
            runtime_plugin = runtime_assistant.plugin_instances.get(str(plugin_link.plugin_id))

        # 调用辅助函数来构建每个 PluginRead 对象
        plugin_read_dto = _build_plugin_read(plugin_link, runtime_plugin)
        plugins_read_list.append(plugin_read_dto)

    # 4. 组装并返回最终的 AssistantRead 对象
    return AssistantRead(
        id=str(assistant.id),
        name=assistant.name,
        description=assistant.description or "No description",
        status=assistant_status,
        plugins=plugins_read_list,
        version=assistant.version,
        spec_version=assistant.spec_version,
        enabled=assistant.enabled,
    )
