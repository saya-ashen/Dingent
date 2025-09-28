from typing import Any, Optional
from uuid import UUID
from fastapi.exceptions import HTTPException
from fastapi import status
from pydantic import BaseModel
from sqlmodel import Session, select

from dingent.core.db.models import Assistant, AssistantPluginLink, Plugin
from dingent.core.schemas import AssistantCreate, AssistantUpdate, PluginUpdateRequest


def get_assistant(db: Session, assistant_id: UUID):
    return db.get(Assistant, assistant_id)


def get_all_assistants(db: Session, user_id: UUID):
    statement = select(Assistant).where(Assistant.user_id == user_id)
    results = db.exec(statement).all()
    return results


def create_assistant(db: Session, assistant_in: AssistantCreate, user_id: UUID):
    new_assistant = Assistant(**assistant_in.model_dump(), user_id=user_id)
    db.add(new_assistant)
    db.commit()
    db.refresh(new_assistant)
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


def delete_assistant(*, db: Session, db_assistant: Assistant) -> Assistant:
    """
    Deletes an assistant from the database.
    """
    db.delete(db_assistant)
    db.commit()
    return db_assistant


def add_plugin_to_assistant(db: Session, *, assistant: Assistant, plugin_id: UUID) -> Assistant:
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
    existing_link = db.exec(select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant.id, AssistantPluginLink.plugin_id == plugin_id)).first()

    if existing_link:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Plugin '{plugin.name}' is already added to assistant '{assistant.name}'.")

    # 3. 创建链接记录
    link = AssistantPluginLink(assistant_id=assistant.id, plugin_id=plugin_id)
    db.add(link)
    db.commit()

    # 刷新 assistant 对象以加载新的 plugin_links 关系
    db.refresh(assistant)

    return assistant


def update_plugin_for_assistant(db: Session, *, assistant: Assistant, plugin_id: UUID, update_data: PluginUpdateRequest) -> Assistant:
    """
    Updates the configuration of a plugin for a specific assistant.
    """
    # 1. Find the specific link to update
    statement = select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant.id, AssistantPluginLink.plugin_id == plugin_id)
    link_to_update = db.exec(statement).first()

    if not link_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This plugin is not associated with the assistant")

    # 2. Get update data, excluding fields that were not sent
    update_dict = update_data.model_dump(exclude_unset=True)
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


def remove_plugin_from_assistant(db: Session, *, assistant: Assistant, plugin_id: UUID) -> None:
    """
    Removes the link between a plugin and an assistant. This is an idempotent operation.
    """
    # 1. Find the specific link to delete
    statement = select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant.id, AssistantPluginLink.plugin_id == plugin_id)
    link_to_delete = db.exec(statement).first()

    # 2. If the link exists, delete it. If not, do nothing (idempotency).
    if link_to_delete:
        db.delete(link_to_delete)
        db.commit()

    return
