from uuid import UUID
from ..db.crud import assistant as crud_assistant
from dingent.core.schemas import AssistantRead, PluginRead
from dingent.core.managers.assistant_runtime_manager import AssistantRuntimeManager
from sqlmodel import Session
from .converters import _build_assistant_read


async def get_assistant_details_for_api(
    db: Session,
    assistant_manager: AssistantRuntimeManager,
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
    assistant_manager: AssistantRuntimeManager,
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
