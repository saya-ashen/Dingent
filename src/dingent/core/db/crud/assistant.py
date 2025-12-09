from uuid import UUID
from fastapi import HTTPException
from jsonschema import validate, ValidationError

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from dingent.core.db.models import Assistant, AssistantPluginLink, Plugin
from dingent.core.schemas import AssistantCreate, AssistantUpdate, PluginUpdateOnAssistant

import json
from fastapi import HTTPException
# ... 其他 import


import json
import ast  # 引入 ast 库
from fastapi import HTTPException


def _preprocess_json_fields(config_data: dict, schema: dict | None):
    """
    尝试解析 JSON 字符串。
    策略：先尝试标准 JSON 解析，如果失败，再尝试 Python 字面量解析（支持单引号）。
    """
    if not schema or not config_data:
        return

    properties = schema.get("properties", {})

    for key, value in config_data.items():
        # 如果不是字符串，说明不需要解析，跳过
        if not isinstance(value, str):
            continue

        field_def = properties.get(key)
        if not field_def:
            continue

        expected_type = field_def.get("type")

        # 针对 object (dict) 和 array (list) 类型尝试解析
        if expected_type in ["object", "array"]:
            parsed_value = None

            # --- 方案 1: 尝试标准 JSON 解析 (最快，最标准) ---
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError as json_err:
                # --- 方案 2: JSON 失败，尝试 Python 字面量解析 (支持单引号) ---
                try:
                    # ast.literal_eval 只能解析基础数据结构，非常安全，不会执行恶意代码
                    parsed_value = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    # 如果两个都失败了，抛出原始的 JSON 错误，提示用户格式不对
                    # 也可以把 json_err 和 ast 的错误一起 log 出来
                    raise HTTPException(
                        status_code=400, detail=(f"Field '{key}' invalid. Expected valid JSON (double quotes) or Python dict (single quotes). Error: {str(json_err)}")
                    )

            # --- 解析成功，检查类型是否匹配 ---
            # json.loads 可能把 "123" 解析成 int，但我们需要 object/list
            # 注意：Python 中 dict 对应 JSON object, list 对应 JSON array
            if expected_type == "object" and not isinstance(parsed_value, dict):
                raise HTTPException(status_code=400, detail=f"Field '{key}' parsed successfully but result is not a Dictionary.")

            if expected_type == "array" and not isinstance(parsed_value, list):
                raise HTTPException(status_code=400, detail=f"Field '{key}' parsed successfully but result is not a List.")

            # --- 原地更新配置 ---
            config_data[key] = parsed_value


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
    db.commit()

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
    # 1. 更新 Assistant 基础字段
    update_data = assistant_in.model_dump(exclude={"plugins"}, exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_assistant, k, v)

    # 2. 更新 Plugins 配置
    if assistant_in.plugins:
        # 建立索引：plugin_registry_id -> link 对象
        link_by_registry_id: dict[str, AssistantPluginLink] = {link.plugin.registry_id: link for link in db_assistant.plugin_links}

        for plugin_cfg in assistant_in.plugins:
            link = link_by_registry_id.get(plugin_cfg.registry_id)
            if link is None:
                continue

            plugin_update_data = plugin_cfg.model_dump(exclude_unset=True)

            # 更新 enabled 状态
            if "enabled" in plugin_update_data:
                link.enabled = plugin_cfg.enabled

            # 处理 config 更新与验证
            if "config" in plugin_update_data:
                new_conf = plugin_update_data["config"] or {}

                schema = link.plugin.config_schema
                _preprocess_json_fields(new_conf, schema)

                current_conf = link.user_plugin_config or {}

                merged_conf = current_conf.copy()
                merged_conf.update(new_conf)

                if schema:
                    try:
                        # 使用 jsonschema 进行校验
                        validate(instance=merged_conf, schema=schema)
                    except ValidationError as e:
                        # 验证失败，抛出 HTTP 400 错误
                        # e.message 通常包含具体的错误字段信息
                        raise HTTPException(status_code=400, detail=f"Plugin '{plugin_cfg.registry_id}' configuration error: {e.message}")

                # 验证通过，才真正更新数据库对象
                link.user_plugin_config = merged_conf

    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    return db_assistant


def add_plugin_to_assistant(db: Session, *, assistant_id: UUID, plugin_registry_id: str) -> Assistant:
    """
    Links an existing plugin to an assistant by creating an AssistantPluginLink record.

    This function performs crucial validation:
    1. Checks if the plugin exists.
    2. Checks if the plugin is already linked to the assistant to prevent duplicates.
    """
    # 1. 验证 Plugin 是否存在
    # plugin = db.get(Plugin, plugin_id)
    plugin = db.exec(select(Plugin).where(Plugin.registry_id == plugin_registry_id)).first()
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plugin with id {plugin_registry_id} not found.")

    # 2. 验证是否已经存在链接，防止重复添加
    plugin_pk = plugin.id
    existing_link = db.exec(select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant_id, AssistantPluginLink.plugin_id == plugin_pk)).first()

    if existing_link:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Plugin '{plugin.display_name}' is already added to assistant '{assistant_id}'.")

    # 3. 创建链接记录
    assistant = db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Assistant with id {assistant_id} not found.")
    link = AssistantPluginLink(assistant_id=assistant.id, plugin_id=plugin.id)
    db.add(link)
    db.commit()

    # 刷新 assistant 对象以加载新的 plugin_links 关系
    db.refresh(assistant)

    return assistant


def update_plugin_on_assistant(db: Session, *, assistant_id: UUID, plugin_id: UUID, plugin_update: PluginUpdateOnAssistant) -> Assistant:
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


def remove_plugin_from_assistant(db: Session, *, assistant_id: UUID, registry_id: str) -> None:
    """
    Removes the link between a plugin and an assistant. This is an idempotent operation.
    """
    # 1. Find the specific link to delete
    plugin_statement = select(Plugin).where(Plugin.registry_id == registry_id)
    plugin = db.exec(plugin_statement).first()
    if not plugin:
        return
    statement = select(AssistantPluginLink).where(AssistantPluginLink.assistant_id == assistant_id, AssistantPluginLink.plugin_id == plugin.id)
    link_to_delete = db.exec(statement).first()

    # 2. If the link exists, delete it. If not, do nothing (idempotency).
    if link_to_delete:
        db.delete(link_to_delete)
        db.commit()

    return
