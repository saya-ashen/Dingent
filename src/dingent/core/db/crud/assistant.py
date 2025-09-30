from uuid import UUID
from fastapi.exceptions import HTTPException
from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from dingent.core.db.models import Assistant, AssistantPluginLink, Plugin
from dingent.core.schemas import AssistantCreate, AssistantUpdate, PluginUpdate


def get_assistant_by_id(*, db: Session, id: UUID):
    return db.get(Assistant, id)


def get_assistant_by_name(db: Session, user_id: UUID, name: str):
    return db.exec(select(Assistant).where(Assistant.user_id == user_id, Assistant.name == name)).first()


def get_user_assistant(db: Session, assistant_id: UUID, user_id: UUID):
    return db.exec(select(Assistant).where(Assistant.id == assistant_id, Assistant.user_id == user_id)).first()


def get_all_assistants(db: Session, user_id: UUID):
    statement = select(Assistant).where(Assistant.user_id == user_id)
    results = db.exec(statement).all()
    return results


def remove_assistant(db: Session, *, id: UUID) -> Assistant | None:
    """
    Deletes an assistant from the database by its ID.

    Args:
        db: The database session.
        id: The UUID of the assistant to delete.

    Returns:
        The deleted Assistant object, or None if not found.
    """
    assistant_to_delete = db.get(Assistant, id)

    if not assistant_to_delete:
        return None

    db.delete(assistant_to_delete)

    return assistant_to_delete


def create_assistant(db: Session, assistant_in: AssistantCreate, user_id: UUID):
    new_assistant = Assistant(**assistant_in.model_dump(), user_id=user_id)
    db.add(new_assistant)
    try:
        # 尝试提交事务，这里可能会触发 IntegrityError
        db.commit()
        # 成功后，刷新实例以从数据库获取最新状态（如默认值）
        db.refresh(new_assistant)

    except IntegrityError:
        # 3. 如果发生完整性错误，必须回滚事务！
        # 失败的 commit() 会让 session 进入一个不一致的状态，必须回滚才能继续使用。
        db.rollback()

        # 4. 抛出一个对 API 友好的异常
        # HTTP 409 Conflict 是用于此类错误的标准化状态码
        raise HTTPException(
            status_code=409,
            detail=f"Assistant with name '{assistant_in.name}' already exists.",
        )

    return new_assistant


def update_assistant(
    db: Session,
    db_assistant: Assistant,
    assistant_in: AssistantUpdate,
):
    update_data = assistant_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_assistant, key, value)

    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)

    return db_assistant


def add_plugin_to_assistant(db: Session, *, assistant_id: UUID, plugin_id: UUID) -> Assistant:
    """
    Links an existing plugin to an assistant by creating an AssistantPluginLink record.

    This function performs crucial validation:
    1. Checks if the plugin exists.
    2. Checks if the plugin is already linked to the assistant to prevent duplicates.
    """
    # 1. 验证 Plugin 是否存在
    plugin = db.get(Plugin, plugin_id)
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plugin with id {plugin_id} not found.")

    # 2. 验证是否已经存在链接，防止重复添加
    existing_link = db.exec(select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant_id, AssistantPluginLink.plugin_id == plugin_id)).first()

    if existing_link:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Plugin '{plugin.display_name}' is already added to assistant '{assistant_id}'.")

    # 3. 创建链接记录
    assistant = db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Assistant with id {assistant_id} not found.")
    link = AssistantPluginLink(assistant_id=assistant.id, plugin_id=plugin_id)
    db.add(link)
    db.commit()

    # 刷新 assistant 对象以加载新的 plugin_links 关系
    db.refresh(assistant)

    return assistant


def update_plugin_on_assistant(db: Session, *, assistant_id: UUID, plugin_id: UUID, plugin_update: PluginUpdate) -> Assistant:
    """
    Updates the configuration of a plugin for a specific assistant.
    """
    # 1. Find the specific link to update
    statement = select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant_id, AssistantPluginLink.plugin_id == plugin_id)
    link_to_update = db.exec(statement).first()

    if not link_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This plugin is not associated with the assistant")

    # 2. Get update data, excluding fields that were not sent
    update_dict = plugin_update.model_dump(exclude_unset=True)
    assistant = db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Assistant with id {assistant_id} not found.")
    if not update_dict:
        # No changes were requested
        return assistant

    # 3. Apply the changes
    for key, value in update_dict.items():
        setattr(link_to_update, key, value)

    db.add(link_to_update)
    db.commit()
    db.refresh(assistant)

    return assistant


def remove_plugin_from_assistant(db: Session, *, assistant_id: UUID, plugin_id: UUID) -> None:
    """
    Removes the link between a plugin and an assistant. This is an idempotent operation.
    """
    # 1. Find the specific link to delete
    statement = select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant_id, AssistantPluginLink.plugin_id == plugin_id)
    link_to_delete = db.exec(statement).first()

    # 2. If the link exists, delete it. If not, do nothing (idempotency).
    if link_to_delete:
        db.delete(link_to_delete)
        db.commit()

    return
