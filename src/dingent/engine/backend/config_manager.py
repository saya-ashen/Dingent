from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Any

import tomlkit
from loguru import logger
from pydantic import ValidationError

from dingent.utils import find_project_root

from .settings import AppSettings

# 说明：
# - 假设 AppSettings 是一个 Pydantic v2 的模型，具备 .model_dump() 和 .save() 方法
# - 且包含属性 assistants（列表），列表元素具备 name 字段


def _find_key_value_for_item(item: dict, keys: list[str]) -> tuple[str, Any]:
    """
    Finds the first key from the priority list that exists in the item.
    Returns the key's name and its value.
    Raises ValueError if no key is found.
    """
    for key in keys:
        if key in item:
            return key, item[key]
    raise ValueError(f"Could not find any of the required merge keys {keys} in list item: {item}")


def deep_merge(base: dict[str, Any], patch: dict[str, Any], list_merge_keys: list[str]) -> dict[str, Any]:
    """
    Recursively merges a 'patch' dictionary into a 'base' dictionary.

    - Dictionaries are merged recursively.
    - For lists of dictionaries, items are merged if they share a common identifier.
      The function searches for an identifier in each dictionary using the keys
      provided in `list_merge_keys` in the given order.
    - If a dictionary in a list does not contain any of the specified merge keys,
      a ValueError is raised.
    - Other value types from `patch` overwrite `base`.
    """
    result = base.copy()

    for k, v in patch.items():
        # Recursive merge for dictionaries
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v, list_merge_keys)

        # List merging logic based on a priority of keys
        elif k in result and isinstance(result[k], list) and isinstance(v, list):
            merged_list = result[k][:]
            base_map = {}

            # Build a map of the base list items using their identifier
            for item in merged_list:
                if isinstance(item, dict):
                    try:
                        _, key_value = _find_key_value_for_item(item, list_merge_keys)
                        base_map[key_value] = item
                    except ValueError as e:
                        raise ValueError(f"Error in base list under key '{k}': {e}") from e

            # Iterate through the patch list to merge or append
            for patch_item in v:
                if not isinstance(patch_item, dict):
                    if patch_item not in merged_list:
                        merged_list.append(patch_item)
                    continue

                try:
                    _, key_value = _find_key_value_for_item(patch_item, list_merge_keys)
                except ValueError as e:
                    raise ValueError(f"Error in patch list under key '{k}': {e}") from e

                if key_value in base_map:
                    base_item = base_map[key_value]
                    merged_item = deep_merge(base_item, patch_item, list_merge_keys)

                    # Find and replace the original item in the list
                    for i, original_item in enumerate(merged_list):
                        if isinstance(original_item, dict):
                            try:
                                _, original_key_value = _find_key_value_for_item(original_item, list_merge_keys)
                                if original_key_value == key_value:
                                    merged_list[i] = merged_item
                                    base_map[key_value] = merged_item  # Update map
                                    break
                            except ValueError:
                                continue  # This item can't be matched
                else:
                    merged_list.append(patch_item)

            result[k] = merged_list
        # Overwrite for all other types
        else:
            result[k] = v
    return result


def _clean_patch(patch: dict) -> dict:
    """
    Recursively cleans a patch dictionary by removing keys whose values
    are None or the placeholder '********'.

    This ensures that only legitimate changes are passed to the merge function.
    """
    if not isinstance(patch, dict):
        return patch

    cleaned_dict = {}
    for key, value in patch.items():
        # --- PRIMARY CONDITION ---
        # If the value is a placeholder or None, skip this key entirely.
        if value is None or not str(value).strip("*"):
            continue

        # --- RECURSIVE CLEANING ---
        # If the value is a dictionary, clean it recursively.
        if isinstance(value, dict):
            cleaned_value = _clean_patch(value)
            # Only add the nested dictionary if it's not empty after cleaning.
            if cleaned_value:
                cleaned_dict[key] = cleaned_value
        # If the value is a list, clean each item inside it (if it's a dict).
        elif isinstance(value, list):
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_item = _clean_patch(item)
                    if cleaned_item:
                        cleaned_list.append(cleaned_item)
                # Keep non-dict items as-is, unless they are also placeholders
                elif item is not None and item != "********":
                    cleaned_list.append(item)
            cleaned_dict[key] = cleaned_list
        # Otherwise, it's a valid value to keep.
        else:
            cleaned_dict[key] = value

    return cleaned_dict


# --- 1. 自定义异常 ---
class ConfigError(Exception):
    """Base exception for configuration errors."""

    pass


class ConfigUpdateError(ConfigError):
    """Raised when a configuration update fails validation."""

    pass


class AssistantNotFoundError(ConfigError, KeyError):
    """Raised when a specific assistant is not found in the configuration."""

    pass


class ConfigManager:
    """
    配置管理器（单例）
    - 线程安全：读写均使用同一把锁保护
    - 提供获取、更新、保存配置的方法
    - 支持对 assistants 的单项更新
    """

    _instance: ConfigManager | None = None
    _lock = RLock()

    # 用于保存当前配置实例（AppSettings）。在 __init__ 中延迟初始化。
    _settings: AppSettings = None  # type: ignore[assignment]
    _config_path: Path | None = None

    def __init__(self):
        # 避免重复初始化
        _project_root: Path | None = find_project_root()
        if _project_root:
            self._config_path = _project_root / "backend" / "config.toml"
        else:
            self._config_path = None
        self._settings: AppSettings = self._load_config()
        logger.info("Configuration Manager initialized.")

    def _load_config(self) -> AppSettings:
        """
        显式地从文件和环境中加载、合并和校验配置。
        """
        # 1. 从 TOML 文件加载 (基础配置)
        file_data = {}
        if self._config_path and self._config_path.is_file():
            try:
                logger.info(f"Loading settings from: {self._config_path}")
                with open(self._config_path) as f:
                    text = f.read()
                file_data = tomlkit.parse(text).unwrap()
            except Exception as e:
                logger.error(f"Error reading config file at {self._config_path}: {e}")
                # 即使文件损坏，也继续，以便环境变量可以覆盖
        else:
            logger.warning(f"Config file not found at {self._config_path}. Using defaults and env vars.")

        # 2. 从环境变量加载 (覆盖配置)
        # 这是一个简化的环境变量加载器，你可以根据需要扩展
        # 例如, pydantic-settings 支持 APP_LLM__MODEL 这样的嵌套格式
        # 这里我们只处理顶层字段作为示例
        env_data = {}
        if "APP_DEFAULT_ASSISTANT" in os.environ:
            env_data["default_assistant"] = os.environ["APP_DEFAULT_ASSISTANT"]
        # 你可以添加更多环境变量的解析逻辑...

        # 3. 合并配置 (环境变量优先级更高)
        merged_data = deep_merge(file_data, env_data, ["id", "name"])

        # 4. 使用纯净的 AppSettings 模型进行校验
        try:
            return AppSettings.model_validate(merged_data)
        except ValidationError as e:
            logger.error(f"Configuration validation failed during initial load! Errors: {e}")
            logger.warning("Falling back to default configuration.")
            return AppSettings()  # 加载失败时返回一个空的默认配置

    # ===================== 对外 API =====================

    def save_config(self) -> None:
        """
        将当前内存中的配置保存回 TOML 文件。
        """
        with self._lock:
            if not self._config_path:
                logger.error("Cannot save settings: config path is not defined.")
                return

            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用 model_dump 创建一个可序列化的字典
            config_data = self._settings.model_dump(mode="json", exclude_none=True)

            # 使用 tomlkit 来保留格式 (如果原始文件存在)
            doc = tomlkit.document()
            if self._config_path.is_file():
                doc = tomlkit.parse(self._config_path.read_text("utf-8"))

            doc.update(config_data)

            self._config_path.write_text(tomlkit.dumps(doc), "utf-8")
            logger.success(f"Configuration saved successfully to {self._config_path}")

    def get_config(self) -> AppSettings:
        """安全地返回当前配置的深拷贝。"""
        with self._lock:
            return self._settings.model_copy(deep=True)

    def update_config(self, new_config_data: dict[str, Any]) -> None:
        """
        Updates the configuration by merging a partial patch.

        It first cleans the patch to remove placeholders ('********') and None values,
        ensuring that only intentional changes are applied.
        """
        if not isinstance(new_config_data, dict):
            raise TypeError("new_config_data must be a dictionary")

        with self._lock:
            try:
                # Step 1: Clean the incoming patch to remove ignored values.
                cleaned_data = _clean_patch(new_config_data)

                # If the patch is empty after cleaning, there's nothing to do.
                if not cleaned_data:
                    # You might want to log this event for debugging.
                    print("Configuration update skipped: patch was empty after cleaning.")
                    return

                # Step 2: Get the current configuration as a dictionary.
                current_data = self._settings.model_dump()

                # Step 3: Merge the *cleaned* data into the current data.
                merged_data = deep_merge(current_data, cleaned_data, ["id", "name"])

                # Step 4: Validate the fully merged data against the Pydantic model.
                new_settings = AppSettings.model_validate(merged_data)

                # Step 5: If validation succeeds, update the settings and save.
                self._settings = new_settings
                self.save_config()

            except ValidationError as e:
                raise ConfigUpdateError(f"Configuration validation failed: {e}") from e

    def update_assistant_config(self, new_config_data: dict[str, Any]) -> dict[str, Any]:
        """
        更新 assistants 列表中的某一个助手配置（通过 name 匹配）。
        处理逻辑：
        1) 读取当前配置 dump 为字典。
        2) 找到对应 name 的 assistant 条目（字典），深度合并更新。
        3) 用更新后的总字典重建 AppSettings，触发 Pydantic 校验。
        4) 保存。

        注意：这里在字典层面更新 assistants，然后整体重建 AppSettings，避免直接改对象带来的不一致问题。
        """
        name = new_config_data.get("name")
        if not name:
            return {"success": False, "error": "缺少 'name' 字段"}

        with self._lock:
            try:
                data = self._settings.model_dump()
                assistants = data.get("assistants") or []
                if not isinstance(assistants, list):
                    return {"success": False, "error": "配置字段 'assistants' 类型异常，期望为列表"}

                target_idx = -1
                for i, item in enumerate(assistants):
                    # model_dump 后 assistants 项为 dict
                    if isinstance(item, dict) and item.get("name") == name:
                        target_idx = i
                        break

                if target_idx == -1:
                    return {"success": False, "error": f"未找到名为 '{name}' 的 assistant"}

                # 深度合并该 assistant
                assistants[target_idx] = self._deep_merge(assistants[target_idx], new_config_data)
                data["assistants"] = assistants

                # 重建并保存
                new_settings = AppSettings(**data)  # type: ignore[name-defined]
                self._settings = new_settings
                self._settings.save()
                return {"success": True}
            except ValidationError as e:
                return {"success": False, "error": str(e)}

    def get_assistant_config(self, assistant_id: str):
        """根据id获取单个 assistant 配置对象（Pydantic 实例），找不到返回 None"""
        with self._lock:
            assistants = self._settings.assistants
            for assistant in assistants:
                if assistant.id == assistant_id:
                    return assistant
            return None

    def get_all_assistants_config(self) -> dict[str, Any]:
        """返回一个 id -> assistant 对象 的映射字典"""
        with self._lock:
            assistants = self._settings.assistants
            return {assistant.id: assistant for assistant in assistants}

    # ===================== 内部工具方法 =====================

    def _deep_merge(self, base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        """
        简单的深度合并：
        - 当 base[k] 与 patch[k] 都是 dict 时，递归合并
        - 其它情况（包括 list、标量），以 patch 覆盖 base
        注意：list 的合并策略这里是“覆盖”，如需更复杂的行为请自行扩展
        """
        if not isinstance(base, dict) or not isinstance(patch, dict):
            return patch

        result = dict(base)  # 复制一份，避免就地修改传入对象
        for k, v in patch.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = v
        return result


config_manager = None


def get_config_manager():
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager
