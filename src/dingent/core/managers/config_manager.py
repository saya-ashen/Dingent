from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from contextlib import contextmanager
from copy import deepcopy
from enum import Enum, auto
from pathlib import Path
from threading import RLock
from typing import Any

import tomlkit
import yaml
from pydantic import SecretStr, ValidationError

from dingent.core.managers.secret_manager import SecretManager


KEYRING_SERVICE_NAME = "dingent-framework"
KEYRING_PLACEHOLDER_PREFIX = "keyring:"


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merges a patch dictionary into a base dictionary.
    - Dictionaries are merged recursively.
    - Lists in the patch completely replace lists in the base.
    - Other values in the patch overwrite values in the base.
    """
    result = base.copy()
    for key, value in patch.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        # If the value is a list, or any other type, just replace it.
        else:
            result[key] = value
    return result


def _clean_patch(patch: dict) -> dict:
    if not isinstance(patch, dict):
        return patch
    cleaned_dict = {}
    for key, value in patch.items():
        if not str(value).strip("*"):
            continue
        if isinstance(value, dict):
            cleaned_value = _clean_patch(value)
            if cleaned_value:
                cleaned_dict[key] = cleaned_value
        elif isinstance(value, list):
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_item = _clean_patch(item)
                    if cleaned_item:
                        cleaned_list.append(cleaned_item)
                elif item != "********":
                    cleaned_list.append(item)
            cleaned_dict[key] = cleaned_list
        else:
            cleaned_dict[key] = value
    return cleaned_dict


class SecretAction(Enum):
    SAVE = auto()  # Substitute SecretStr with placeholders
    LOAD = auto()  # Resolve placeholders into secret values


def _process_secrets_recursively(
    data: Any,
    path: list[str],
    secret_manager: SecretManager,
    action: SecretAction,
) -> Any:
    """
    Recursively traverses a dict/list structure to process secrets.

    - If action is SAVE: Replaces SecretStr instances with keyring placeholders.
    - If action is LOAD: Replaces keyring placeholders with the actual secret values.
    """
    # --- Action-specific base cases ---

    # SAVE action: Find SecretStr objects and replace them.
    if action == SecretAction.SAVE and isinstance(data, SecretStr):
        key_path = ".".join(path)
        secret_value = data.get_secret_value()
        if secret_value.strip("*") == "":
            return secret_manager.get_secret(key_path)  # Return existing secret for empty/masked values

        if secret_value:
            secret_manager.set_secret(key_path, secret_value)
            return f"{KEYRING_PLACEHOLDER_PREFIX}{key_path}"
        return None  # Return None for empty secrets

    # LOAD action: Find placeholder strings and resolve them.
    if action == SecretAction.LOAD and isinstance(data, str) and data.startswith(KEYRING_PLACEHOLDER_PREFIX):
        key_path = data[len(KEYRING_PLACEHOLDER_PREFIX) :]
        return secret_manager.get_secret(key_path)

    # --- Recursive steps for containers (same for both actions) ---

    if isinstance(data, dict):
        return {key: _process_secrets_recursively(value, path + [key], secret_manager, action) for key, value in data.items()}

    if isinstance(data, list):
        return [_process_secrets_recursively(item, path + [str(i)], secret_manager, action) for i, item in enumerate(data)]

    # Other types (int, bool, non-placeholder str, etc.) are returned as-is.
    return data


# =========================================================
# 异常
# =========================================================
class ConfigError(Exception):
    pass


class ConfigUpdateError(ConfigError):
    pass


class AssistantNotFoundError(ConfigError, KeyError):
    pass


# =========================================================
# 文件结构常量
# =========================================================
ASSISTANTS_DIR_NAME = "assistants"
PLUGINS_DIR_NAME = "plugins"
WORKFLOWS_DIR_NAME = "workflows"  # 仍然保留目录常量（如需要显示），不主动管理其内部文件
GLOBAL_CONFIG_FILE = "dingent.toml"


class MigrationError(Exception):
    pass


class ConfigMigrationRegistry:
    def __init__(self):
        self._migrations: dict[int, Callable[[dict], dict]] = {}

    def register(self, from_version: int, func: Callable[[dict], dict]) -> None:
        self._migrations[from_version] = func

    def migrate(self, data: dict, current_version: int, target_version: int) -> dict:
        """
        顺序执行 from_version -> from_version+1 ... 直到 target_version
        若中间缺失迁移函数则抛出异常。
        """
        version = current_version
        while version < target_version:
            if version not in self._migrations:
                raise MigrationError(f"Missing migration function for version {version} -> {version + 1}")
            data = self._migrations[version](data)
            version += 1
        return data


migration_registry = ConfigMigrationRegistry()

# 示例：注册一个占位迁移（如需要）
# @migration_registry.register(1)
# def migrate_1_to_2(data: dict) -> dict:
#     # mutate or copy
#     data["some_new_field"] = data.get("some_new_field", {})
#     data["config_version"] = 2
#     return data


# =========================================================
# ConfigManager
# =========================================================
class ConfigManager:
    """
    职责聚焦版：
      - 负责拆分式配置文件的 I/O（global / assistants / plugins）
      - 提供线程安全获取与更新
      - 提供快照/恢复、事务批处理、迁移框架、on_change 订阅
      - 不做：插件业务逻辑（增删单个插件）、工作流对象管理、跨服务协作

    目录结构：
      project_root/
        dingent.toml
        config/
          assistants/{assistant_id}.yaml
          plugins/{plugin_name}/{assistant_id}.yaml
          workflows/ (ConfigManager 不写入，不解析内部结构，只保留 AppSettings 中已有字段)
    """

    def __init__(
        self,
        project_root: Path,
        log_manager,
        backup_dir_name: str = ".config_backups",
        max_backups: int = 5,
        auto_migrate: bool = True,
        target_config_version: int = 1,  # 你可以根据需要调整或从常量处读取
    ):
        self.project_root = Path(project_root)
        self.secret_manager = SecretManager(self.project_root)
        self.log_manager = log_manager
        self._global_config_path = self.project_root / GLOBAL_CONFIG_FILE
        self._config_root = self.project_root / "config"
        self._assistants_dir = self._config_root / ASSISTANTS_DIR_NAME
        self._plugins_dir = self._config_root / PLUGINS_DIR_NAME
        self._workflows_dir = self._config_root / WORKFLOWS_DIR_NAME  # 只为展示或透传

        self._backup_root = self.project_root / backup_dir_name
        self._max_backups = max_backups

        self._lock = RLock()

    def _load_all(self) -> dict:
        global_part = self._load_global()
        assistants_raw = self._load_assistants()
        plugin_map = self._load_plugin_instances()

        assistants: list[dict] = []
        for a_id, a_data in assistants_raw.items():
            copy_data = deepcopy(a_data)
            copy_data["plugins"] = plugin_map.get(a_id, [])
            assistants.append(copy_data)

        if "workflows" not in global_part:
            global_part["workflows"] = []
        global_part["assistants"] = assistants
        return _process_secrets_recursively(global_part, [], self.secret_manager, action=SecretAction.LOAD)

    def _load_global(self) -> dict:
        if not self._global_config_path.is_file():
            self.log_manager.log_with_context("warning", "Global config file missing at {path}, using defaults.", context={"path": str(self._global_config_path)})
            return {}
        try:
            text = self._global_config_path.read_text("utf-8")
            doc = tomlkit.parse(text).unwrap()
            return doc
        except Exception as e:
            self.log_manager.log_with_context("error", "Failed to read global config: {error}", context={"error": str(e)})
            return {}

    def _load_assistants(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        if not self._assistants_dir.is_dir():
            return result
        for f in self._assistants_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text("utf-8")) or {}
                if not isinstance(data, dict):
                    self.log_manager.log_with_context("warning", "Assistant file {file} top-level not dict. Skip.", context={"file": str(f)})
                    continue
                aid = data.get("id")
                if not aid:
                    self.log_manager.log_with_context("warning", "Assistant file {file} missing id. Skip.", context={"file": str(f)})
                    continue
                data.pop("plugins", None)  # 强制移除，实际以拆分插件为准
                result[aid] = data
            except Exception as e:
                self.log_manager.log_with_context("error", "Read assistant file {file} failed: {error}", context={"file": str(f), "error": str(e)})
        return result

    def _load_plugin_instances(self) -> dict[str, list[dict]]:
        mapping: dict[str, list[dict]] = {}
        if not self._plugins_dir.is_dir():
            return mapping
        for pdir in self._plugins_dir.iterdir():
            if not pdir.is_dir():
                continue
            plugin_name = pdir.name
            for cfg in pdir.glob("*.yaml"):
                try:
                    pdata = yaml.safe_load(cfg.read_text("utf-8")) or {}
                    if not isinstance(pdata, dict):
                        continue
                    aid = pdata.get("assistant_id")
                    if not aid:
                        self.log_manager.log_with_context("warning", "Plugin instance {file} missing assistant_id. Skip.", context={"file": str(cfg)})
                        continue
                    if pdata.get("plugin_name") != plugin_name:
                        pdata["plugin_name"] = plugin_name
                    if not pdata.get("name"):
                        pdata["name"] = plugin_name
                    mapping.setdefault(aid, []).append(pdata)
                except Exception as e:
                    self.log_manager.log_with_context("error", "Read plugin instance file {file} failed: {error}", context={"file": str(cfg), "error": str(e)})
        return mapping

    def _write_global(self, global_part: dict[str, Any]) -> None:
        self._global_config_path.parent.mkdir(parents=True, exist_ok=True)
        if self._global_config_path.is_file():
            doc = tomlkit.parse(self._global_config_path.read_text("utf-8"))
        else:
            doc = tomlkit.document()
        # 清空再写（可选：保留历史字段）
        for k in list(doc.keys()):
            if k not in global_part:
                # 保守做法：不删除未知字段
                # 若希望强制对齐，可执行: del doc[k]
                pass
        doc.update(global_part)
        self._global_config_path.write_text(tomlkit.dumps(doc), "utf-8")

    def _write_assistants_and_plugins(self, assistants: list[dict]) -> None:
        self._assistants_dir.mkdir(parents=True, exist_ok=True)
        self._plugins_dir.mkdir(parents=True, exist_ok=True)

        desired_assistant_ids = set()
        desired_plugin_files: set[Path] = set()

        for a in assistants:
            a_id = a.get("id")
            if not a_id:
                self.log_manager.log_with_context("warning", "Assistant without id discarded during save.")
                continue
            desired_assistant_ids.add(a_id)
            a_copy = dict(a)
            plugin_list = a_copy.pop("plugins", [])

            # 写 assistant
            (self._assistants_dir / f"{a_id}.yaml").write_text(
                yaml.safe_dump(a_copy, allow_unicode=True, sort_keys=False),
                "utf-8",
            )

            # 写 plugin instances
            for p in plugin_list:
                p_copy = dict(p)
                p_copy["assistant_id"] = a_id
                plugin_id = p_copy.get("plugin_id")
                if not plugin_id:
                    self.log_manager.log_with_context("warning", "Plugin config for assistant {aid} missing plugin_id. Discarded.", context={"aid": a_id})
                    continue
                p_dir = self._plugins_dir / plugin_id
                p_dir.mkdir(parents=True, exist_ok=True)
                pf = p_dir / f"{a_id}.yaml"
                desired_plugin_files.add(pf)
                pf.write_text(
                    yaml.safe_dump(p_copy, allow_unicode=True, sort_keys=False),
                    "utf-8",
                )

        # 清理多余 assistants
        for old_file in self._assistants_dir.glob("*.yaml"):
            if old_file.stem not in desired_assistant_ids:
                try:
                    old_file.unlink()
                except Exception as e:
                    self.log_manager.log_with_context("error", "Remove stale assistant file {file} failed: {error}", context={"file": str(old_file), "error": str(e)})

        # 清理多余插件实例
        for pdir in self._plugins_dir.iterdir():
            if not pdir.is_dir():
                continue
            for cfg in pdir.glob("*.yaml"):
                if cfg not in desired_plugin_files:
                    try:
                        cfg.unlink()
                    except Exception as e:
                        self.log_manager.log_with_context("error", "Remove stale plugin instance {file} failed: {error}", context={"file": str(cfg), "error": str(e)})
            # 删除空目录
            try:
                if not any(pdir.iterdir()):
                    pdir.rmdir()
            except Exception:
                pass

    def _delete_assistant_files(self, assistant_id: str) -> None:
        # 删除 assistant YAML
        f = self._assistants_dir / f"{assistant_id}.yaml"
        if f.is_file():
            try:
                f.unlink()
            except Exception as e:
                self.log_manager.log_with_context("error", "Remove assistant file {file} failed: {error}", context={"file": str(f), "error": str(e)})
        # 删除该 assistant 的所有插件实例
        if self._plugins_dir.is_dir():
            for pdir in self._plugins_dir.iterdir():
                if not pdir.is_dir():
                    continue
                inst = pdir / f"{assistant_id}.yaml"
                if inst.is_file():
                    try:
                        inst.unlink()
                    except Exception as e:
                        self.log_manager.log_with_context("error", "Remove plugin instance {file} failed: {error}", context={"file": str(inst), "error": str(e)})
                try:
                    if not any(pdir.iterdir()):
                        pdir.rmdir()
                except Exception:
                    pass

    # ---------- 内部：备份 & 变更通知 ----------
    def _write_backup(self) -> None:
        try:
            self._backup_root.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            backup_dir = self._backup_root / ts
            backup_dir.mkdir()
            # 复制 global
            if self._global_config_path.exists():
                shutil.copy2(self._global_config_path, backup_dir / self._global_config_path.name)
            # 复制 assistants & plugins
            for d in (self._assistants_dir, self._plugins_dir):
                if d.exists():
                    target_sub = backup_dir / d.name
                    shutil.copytree(d, target_sub)
            # 保留最新 N 份
            backups = sorted(self._backup_root.iterdir(), key=lambda p: p.name, reverse=True)
            for old in backups[self._max_backups :]:
                if old.is_dir():
                    shutil.rmtree(old, ignore_errors=True)
        except Exception as e:
            self.log_manager.log_with_context("warning", "Write config backup failed: {error}", context={"error": str(e)})
