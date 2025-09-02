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

from dingent.core.secret_manager import SecretManager

from .settings import AppSettings, AssistantSettings
from .types import AssistantCreate, AssistantUpdate, PluginUserConfig

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


OnChangeCallback = Callable[[AppSettings, AppSettings], None]


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
        self._on_change_callbacks: list[OnChangeCallback] = []

        # 载入+迁移
        raw_data = self._load_all()
        if auto_migrate:
            raw_data = self._maybe_migrate(raw_data, target_config_version)
        self._settings = self._validate(raw_data)

        self.log_manager.log_with_context("info", "ConfigManager initialized with {count} assistants.", context={"count": len(self._settings.assistants)})

    # ---------- 对外基础接口 ----------
    def get_settings(self) -> AppSettings:
        with self._lock:
            return self._settings.model_copy(deep=True)

    def list_assistants(self) -> list[AssistantSettings]:
        with self._lock:
            return [a.model_copy(deep=True) for a in self._settings.assistants]

    def get_assistant(self, assistant_id: str) -> AssistantSettings | None:
        with self._lock:
            return next((a.model_copy(deep=True) for a in self._settings.assistants if a.id == assistant_id), None)

    def upsert_assistant(self, data: AssistantCreate | AssistantUpdate | dict) -> AssistantSettings:
        """
        如果 id 存在则更新；如果不存在则创建。
        - 更新时：使用 _clean_patch 过滤掉全为 '*'（例如 '********'）的字段或结构，不覆盖原值。
        - 创建时：同样会清理；若清理后缺少必填字段将触发校验错误。
        """
        if isinstance(data, AssistantCreate | AssistantUpdate):
            raw_patch = data.model_dump(exclude_unset=True)
        else:
            raw_patch = dict(data)

        # 清理（去掉值为全 * 的字段 / 结构）
        patch = _process_secrets_recursively(raw_patch, path=[], secret_manager=self.secret_manager, action=SecretAction.SAVE)

        with self._lock:
            old_settings = self._settings
            assistants_map = {a.id: a for a in old_settings.assistants}

            # id 优先从原始 patch 拿，避免被清理掉（理论上 id 不会是掩码，但更稳健）
            a_id = raw_patch.get("id") or patch.get("id")

            # ---------- 更新逻辑 ----------
            if a_id and a_id in assistants_map:
                # 如果清理后没有任何有效字段，视为无变更，直接返回旧副本
                if not patch or (set(patch.keys()) == {"id"} and len(patch) == 1):
                    return assistants_map[a_id].model_copy(deep=True)

                base = assistants_map[a_id].model_dump()
                merged = deep_merge(base, patch)
                new_assistant = AssistantSettings.model_validate(merged)

                new_list = []
                for a in old_settings.assistants:
                    new_list.append(new_assistant if a.id == a_id else a)

            # ---------- 创建逻辑 ----------
            else:
                if "id" not in patch:
                    raise ValueError("Creating a new assistant requires an 'id'.")
                create_obj = AssistantCreate.model_validate(patch)
                new_assistant = AssistantSettings.model_validate(create_obj.model_dump())
                new_list = list(old_settings.assistants) + [new_assistant]

            new_app = old_settings.model_copy(update={"assistants": new_list})
            self._replace_settings(old_settings, new_app)
            return new_assistant.model_copy(deep=True)

    def delete_assistant(self, assistant_id: str) -> bool:
        with self._lock:
            old = self._settings
            new_list = [a for a in old.assistants if a.id != assistant_id]
            if len(new_list) == len(old.assistants):
                return False
            new_app = old.model_copy(update={"assistants": new_list})
            self._replace_settings(old, new_app)
            # 删除文件
            self._delete_assistant_files(assistant_id)
            return True

    def update_global(self, new_settings: dict[str, Any]) -> AppSettings:
        """
        更新全局顶层字段（包含 default_assistant, llm 等），不会对 assistants 做任何修改。
        只支持全量更新
        """
        with self._lock:
            old = self._settings
            base = old.model_dump(exclude_none=True)
            patch = _clean_patch(new_settings) or {}
            merged = deep_merge(base, patch)
            # 只保留原 assistants / 不覆盖
            merged["assistants"] = base["assistants"]
            try:
                new_app = AppSettings.model_validate(merged)
            except ValidationError as e:
                raise ValueError(f"Global patch invalid: {e}") from e
            self._replace_settings(old, new_app)
            return new_app.model_copy(deep=True)

    def update_plugins_for_assistant(self, assistant_id: str, plugin_configs: list[PluginUserConfig]) -> AssistantSettings:
        """
        仅提供“整体替换”能力，不做增删业务细化（由外部服务组合）。
        """
        with self._lock:
            old = self._settings
            target = next((a for a in old.assistants if a.id == assistant_id), None)
            if not target:
                raise ValueError(f"Assistant '{assistant_id}' not found.")

            new_plugins: list[PluginUserConfig] = []
            for pc in plugin_configs:
                if isinstance(pc, PluginUserConfig):
                    new_plugins.append(pc)
                else:
                    new_plugins.append(PluginUserConfig.model_validate(pc))

            new_assistant = target.model_copy(update={"plugins": new_plugins})
            updated_assistants = []
            for a in old.assistants:
                updated_assistants.append(new_assistant if a.id == assistant_id else a)
            new_app = old.model_copy(update={"assistants": updated_assistants})
            self._replace_settings(old, new_app)
            return new_assistant.model_copy(deep=True)

    # ---------- 事务、快照与导入导出 ----------
    @contextmanager
    def transaction(self):
        """
        在上下文内多次修改 settings（使用 self._settings = ... 或暴露的 API），退出时统一保存。
        如果中途出现异常则不写入磁盘。
        """
        with self._lock:
            original = self._settings
            working_copy = original.model_copy(deep=True)
            self._settings = working_copy  # 临时工作副本
            try:
                yield working_copy
                # 成功 -> 写入文件并触发回调
                self._replace_settings(original, working_copy, already_locked=True)
            except Exception:
                # 回滚到 original
                self._settings = original
                raise

    def export_snapshot(self) -> dict:
        """
        返回完整可 JSON 序列化的配置字典（含 assistants/plugins）。
        """
        with self._lock:
            return self._settings.model_dump(mode="json")

    def import_snapshot(self, data: dict, overwrite: bool = True) -> AppSettings:
        """
        从完整配置字典导入；默认覆盖（overwrite=True）。
        """
        with self._lock:
            base = self._settings.model_dump() if not overwrite else {}
            merged = deep_merge(base, data) if not overwrite else data
            new_app = self._validate(merged)
            old = self._settings
            self._replace_settings(old, new_app)
            return new_app.model_copy(deep=True)

    def dry_run_merge(self, patch: dict[str, Any]) -> tuple[bool, ValidationError | None]:
        """
        测试一个 patch 能否成功合并并通过校验。
        """
        with self._lock:
            base = self._settings.model_dump()
            merged = deep_merge(base, patch)
            try:
                AppSettings.model_validate(merged)
                return True, None
            except ValidationError as e:
                return False, e

    # ---------- 订阅机制 ----------
    def register_on_change(self, callback: OnChangeCallback) -> None:
        with self._lock:
            if callback not in self._on_change_callbacks:
                self._on_change_callbacks.append(callback)

    def unregister_on_change(self, callback: OnChangeCallback) -> None:
        with self._lock:
            if callback in self._on_change_callbacks:
                self._on_change_callbacks.remove(callback)

    # ---------- 内部：迁移 & 验证 ----------
    def _maybe_migrate(self, raw: dict, target_version: int) -> dict:
        current_version = int(raw.get("config_version") or 1)
        if current_version >= target_version:
            return raw
        self.log_manager.log_with_context("info", "Migrating config {from_v} -> {to_v}.", context={"from_v": current_version, "to_v": target_version})
        migrated = migration_registry.migrate(raw, current_version, target_version)
        if "config_version" not in migrated:
            migrated["config_version"] = target_version
        return migrated

    def _validate(self, raw: dict) -> AppSettings:
        # 环境变量覆盖
        try:
            return AppSettings.model_validate(raw)
        except ValidationError as e:
            self.log_manager.log_with_context("error", "Configuration validation failed: {error}", context={"error": str(e)})
            raise

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

    # ---------- 内部：写入 ----------
    def _replace_settings(self, old: AppSettings, new: AppSettings, already_locked: bool = False) -> None:
        """
        将内存配置替换并持久化到文件；触发 on_change 回调。
        """
        lock_cm = self._lock if not already_locked else None
        if lock_cm:
            lock_cm.acquire()
        try:
            if old is new:
                # 同一对象引用（事务内会出现），仍执行持久化
                pass
            self._settings = new
            self._persist()
            self._emit_change(old, new)
        finally:
            if lock_cm:
                lock_cm.release()

    def _persist(self) -> None:
        self._write_backup()

        settings_dict = self._settings.model_dump(exclude_none=True)
        persistable_data = _process_secrets_recursively(settings_dict, [], self.secret_manager, action=SecretAction.SAVE)

        assistants = persistable_data.pop("assistants", [])

        self._write_global(persistable_data)
        self._write_assistants_and_plugins(assistants)

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

    def _emit_change(self, old: AppSettings, new: AppSettings) -> None:
        if old is new:
            # 事务中 old 与 new 引用不同，这里不做过多判断
            pass
        for cb in list(self._on_change_callbacks):
            try:
                cb(old, new)
            except Exception as e:
                self.log_manager.log_with_context("error", "on_change callback error: {error}", context={"error": str(e)})
