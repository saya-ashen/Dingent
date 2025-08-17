from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Any

import tomlkit
from loguru import logger
from pydantic import ValidationError

from .plugin_manager import get_plugin_manager
from .settings import AppSettings
from .types import PluginUserConfig
from .utils import find_project_root


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

        env_data = {}
        if "APP_DEFAULT_ASSISTANT" in os.environ:
            env_data["default_assistant"] = os.environ["APP_DEFAULT_ASSISTANT"]
        merged_data = deep_merge(file_data, env_data, ["id", "name"])

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

    def update_config(self, new_config_data: dict[str, Any], override_empty=False) -> None:
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
                cleaned_data = new_config_data
                if not override_empty:
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

    def get_all_assistants_config(self) -> dict[str, Any]:
        """返回一个 id -> assistant 对象 的映射字典"""
        with self._lock:
            assistants = self._settings.assistants
            return {assistant.id: assistant for assistant in assistants}

    def add_plugin_config_to_assistant(self, assistant_id: str, plugin_name: str) -> None:
        """
        Creates and adds a default configuration for a new plugin to a specific assistant.

        Args:
            assistant_id: The unique ID of the assistant to modify.
            plugin_name: The name of the plugin to add (must match a registered plugin).

        Raises:
            ValueError: If the plugin is not found or is already configured for the assistant.
            AssistantNotFoundError: If the assistant with the given ID is not found.
        """
        plugin_manager = get_plugin_manager()

        # 1. Get the plugin's definition (manifest) to ensure it exists.
        plugin_manifest = plugin_manager.get_plugin_mainifest(plugin_name)
        if not plugin_manifest:
            raise ValueError(f"Plugin '{plugin_name}' is not registered or could not be found.")

        with self._lock:
            # 2. Find the target assistant in the current settings.
            target_assistant = None
            for assistant in self._settings.assistants:
                if assistant.id == assistant_id:
                    target_assistant = assistant
                    break

            if not target_assistant:
                raise AssistantNotFoundError(f"Assistant with ID '{assistant_id}' not found.")

            # 3. Check if the plugin is already configured for this assistant.
            for existing_plugin in target_assistant.plugins:
                if existing_plugin.name == plugin_name:
                    raise ValueError(f"Plugin '{plugin_name}' is already configured for assistant '{target_assistant.name}'.")

            # 4. Create a default PluginUserConfig for the new plugin.
            #    This serves as the initial configuration block.
            new_plugin_config = PluginUserConfig(
                name=plugin_name,  # The instance name defaults to the plugin name
                plugin_name=plugin_name,  # Links to the manifest
                enabled=True,
                tools_default_enabled=True,  # A sensible default
                config={},  # Starts with no user-defined values
                tools=[],  # Starts with no tool overrides
            )

            # 5. Add the new plugin configuration to the assistant.
            target_assistant.plugins.append(new_plugin_config)

            # 6. Save the changes back to the config file.
            self.save_config()
            logger.success(f"Successfully added plugin '{plugin_name}' to assistant '{target_assistant.name}'.")

    def remove_plugin_from_assistant(self, assistant_id: str, plugin_name: str) -> None:
        """
        Removes a plugin configuration from a specific assistant.

        Args:
            assistant_id: The unique ID of the assistant to modify.
            plugin_name: The name of the plugin instance to remove.

        Raises:
            ValueError: If the plugin is not found in the assistant's configuration.
            AssistantNotFoundError: If the assistant with the given ID is not found.
        """
        with self._lock:
            # 1. Find the target assistant.
            target_assistant = None
            for assistant in self._settings.assistants:
                if assistant.id == assistant_id:
                    target_assistant = assistant
                    break

            if not target_assistant:
                raise AssistantNotFoundError(f"Assistant with ID '{assistant_id}' not found.")

            # 2. Find the plugin to remove in the assistant's plugin list.
            plugin_to_remove = None
            for p_config in target_assistant.plugins:
                if p_config.name == plugin_name:
                    plugin_to_remove = p_config
                    break

            if not plugin_to_remove:
                raise ValueError(f"Plugin '{plugin_name}' is not configured for assistant '{target_assistant.name}' and cannot be removed.")

            # 3. Remove the plugin and save.
            target_assistant.plugins.remove(plugin_to_remove)
            self.save_config()
            logger.success(f"Successfully removed plugin '{plugin_name}' from assistant '{target_assistant.name}'.")


config_manager = None


def get_config_manager():
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager
