from typing import Optional
from uuid import UUID
from sqlmodel import Session

from dingent.core.runtime.plugin import PluginRuntime
from dingent.server.api.routers.dashboard.schemas import AssistantRead, PluginRead

from ..db.models import Assistant, AssistantPluginLink
from ..runtime.assistant import AssistantRuntime
from ..assistant_manager import AssistantManager
from ..db.crud import assistant as crud_assistant


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
        name=plugin_db.name,
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


# 这是提供给 API 层的公共服务函数
async def get_assistant_details_for_api(
    db: Session,
    assistant_manager: AssistantManager,
    assistant_id: UUID,
) -> AssistantRead | None:
    """
    一个完整的服务函数：获取数据、处理逻辑、并返回 API 模型。
    """
    # 1. 从数据库获取
    assistant_db = crud_assistant.get_assistant(db, assistant_id)
    if not assistant_db:
        return None

    # 2. 从管理器获取运行时状态
    runtime_assistant = None
    try:
        runtime_assistant = await assistant_manager.get_runtime_assistant(str(assistant_id))
    except Exception:
        # 可以记录日志等
        pass

    # 3. 调用映射函数进行转换
    assistant_dto = _build_assistant_read(assistant_db, runtime_assistant)

    return assistant_dto


async def get_all_assistant_details_for_api(
    db: Session,
    assistant_manager: AssistantManager,
    user_id: UUID,  # 假设需要根据用户获取
) -> list[AssistantRead]:
    """
    一个完整的服务函数：获取所有 Assistant 的数据、处理逻辑、并返回 API 模型列表。
    采用批量操作以提高效率。
    """
    # 1. 一次性从数据库获取该用户的所有 Assistant
    all_assistants_db = crud_assistant.get_all_assistants(db, user_id)

    # 2. 一次性从管理器获取所有已加载的运行时实例
    # (假设 manager 有一个返回 dict[str, AssistantRuntime] 的方法)
    all_runtime_assistants = await assistant_manager.get_all_runtime_assistants()

    # 3. 在内存中进行映射和组装
    assistant_dto_list: list[AssistantRead] = []
    for assistant_db in all_assistants_db:
        # 从运行时字典中安全地获取对应的实例 (可能不存在，即 "inactive")
        runtime_assistant = all_runtime_assistants.get(str(assistant_db.id))

        # 重用你的单个构建逻辑
        assistant_dto = _build_assistant_read(assistant_db, runtime_assistant)
        assistant_dto_list.append(assistant_dto)

    return assistant_dto_list
