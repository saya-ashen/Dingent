from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Any

import tomlkit
import yaml
from loguru import logger
from pydantic import ValidationError

from .log_manager import log_with_context
from .plugin_manager import get_plugin_manager
from .settings import AppSettings, AssistantSettings
from .types import AssistantCreate, AssistantUpdate, PluginUserConfig
from .utils import find_project_root
from .workflow_manager import get_workflow_manager  # NEW: 引入工作流管理器


# =========================================================
# 深度合并（保留原逻辑）
# =========================================================
def _find_key_value_for_item(item: dict, keys: list[str]) -> tuple[str, Any]:
    for key in keys:
        if key in item:
            return key, item[key]
    raise ValueError(f"Could not find any of the required merge keys {keys} in list item: {item}")


def deep_merge(base: dict[str, Any], patch: dict[str, Any], list_merge_keys: list[str]) -> dict[str, Any]:
    result = base.copy()
    for k, v in patch.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v, list_merge_keys)
        elif k in result and isinstance(result[k], list) and isinstance(v, list):
            merged_list = result[k][:]
            base_map: dict[Any, dict] = {}
            for item in merged_list:
                if isinstance(item, dict):
                    try:
                        _, key_value = _find_key_value_for_item(item, list_merge_keys)
                        base_map[key_value] = item
                    except ValueError as e:
                        raise ValueError(f"Error in base list under key '{k}': {e}") from e

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
                    for i, original_item in enumerate(merged_list):
                        if isinstance(original_item, dict):
                            try:
                                _, original_key_value = _find_key_value_for_item(original_item, list_merge_keys)
                                if original_key_value == key_value:
                                    merged_list[i] = merged_item
                                    base_map[key_value] = merged_item
                                    break
                            except ValueError:
                                continue
                else:
                    merged_list.append(patch_item)
            result[k] = merged_list
        else:
            result[k] = v
    return result


def _clean_patch(patch: dict) -> dict:
    if not isinstance(patch, dict):
        return patch
    cleaned_dict = {}
    for key, value in patch.items():
        if value is None or not str(value).strip("*"):
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
                elif item is not None and item != "********":
                    cleaned_list.append(item)
            cleaned_dict[key] = cleaned_list
        else:
            cleaned_dict[key] = value
    return cleaned_dict


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
WORKFLOWS_DIR_NAME = "workflows"  # 仅用于日志展示（实际加载由 workflow_manager 负责）


# =========================================================
# ConfigManager
# =========================================================
class ConfigManager:
    """
    多源配置管理：
      - dingent.toml: 全局 (llm, default_assistant, 其它全局字段)
      - config/assistants/{assistant_id}.yaml: 每个助理
      - config/plugins/{plugin_name}/{assistant_id}.yaml: 每个助理的该插件实例配置
      - config/workflows/{workflow_id}.json: 工作流（通过 WorkflowManager 统一管理）

    删除插件：删除其目录 (config/plugins/{plugin_name}) + reload()
    删除助理：删除 assistant 文件 + 其所有插件实例文件

    save_config(): 对齐（写入期望的全部文件 & 清理孤立文件）
    """

    _instance: ConfigManager | None = None
    _lock = RLock()

    _settings: AppSettings | None = None
    _global_config_path: Path | None = None
    _config_root: Path | None = None
    _assistants_dir: Path | None = None
    _plugins_dir: Path | None = None
    _workflows_dir: Path | None = None  # 仅用于信息展示

    def __init__(self):
        project_root = find_project_root()
        self.project_root = project_root
        if project_root:
            self._global_config_path = project_root / "dingent.toml"
            self._config_root = project_root / "config"
            self._assistants_dir = self._config_root / ASSISTANTS_DIR_NAME
            self._plugins_dir = self._config_root / PLUGINS_DIR_NAME
            self._workflows_dir = self._config_root / WORKFLOWS_DIR_NAME
        else:
            self._global_config_path = None
            self._config_root = None
            self._assistants_dir = None
            self._plugins_dir = None
            self._workflows_dir = None

        self._settings = self._load_config()

        log_with_context(
            "info",
            "Configuration Manager initialized (split-files mode)",
            context={
                "global_config_path": str(self._global_config_path) if self._global_config_path else None,
                "assistants_dir": str(self._assistants_dir) if self._assistants_dir else None,
                "plugins_dir": str(self._plugins_dir) if self._plugins_dir else None,
                "workflows_dir": str(self._workflows_dir) if self._workflows_dir else None,
                "total_assistants": len(self._settings.assistants) if self._settings else 0,
                "total_workflows": len(self._settings.workflows) if self._settings else 0,
            },
            correlation_id="config_init_split",
        )

    # =================== 加载逻辑 ===================
    def _load_global_toml(self) -> dict[str, Any]:
        data = {}
        if self._global_config_path and self._global_config_path.is_file():
            try:
                with self._global_config_path.open("r", encoding="utf-8") as f:
                    data = tomlkit.parse(f.read()).unwrap()
            except Exception as e:
                logger.error(f"读取 {self._global_config_path} 失败: {e}")
        else:
            logger.warning("未找到 dingent.toml，使用空全局配置。")
        return data

    def _load_assistants(self) -> dict[str, dict]:
        """
        返回 {assistant_id: assistant_dict(不含plugins)}
        """
        result: dict[str, dict] = {}
        if not self._assistants_dir or not self._assistants_dir.is_dir():
            return result
        for f in self._assistants_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text("utf-8")) or {}
                if not isinstance(data, dict):
                    logger.warning(f"Assistant 文件 {f} 顶层不是字典，跳过。")
                    continue
                if "id" not in data or not data["id"]:
                    logger.warning(f"Assistant 文件 {f} 缺少 id，将自动生成。")
                result_id = data.get("id")
                if not result_id:
                    import uuid

                    result_id = str(uuid.uuid4())
                    data["id"] = result_id
                    f.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "utf-8")
                data.pop("plugins", None)
                result[result_id] = data
            except Exception as e:
                logger.error(f"读取助理文件 {f} 失败: {e}")
        return result

    def _load_plugin_instances(self) -> dict[str, list[dict]]:
        """
        遍历 config/plugins/{plugin_name} 下的所有 *.yaml:
          文件内容需要包含 assistant_id
        返回 mapping: assistant_id -> [plugin_config_dict, ...]
        """
        mapping: dict[str, list[dict]] = {}
        if not self._plugins_dir or not self._plugins_dir.is_dir():
            return mapping

        for plugin_dir in self._plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            plugin_name = plugin_dir.name
            for cfg_file in plugin_dir.glob("*.yaml"):
                try:
                    pdata = yaml.safe_load(cfg_file.read_text("utf-8")) or {}
                    if not isinstance(pdata, dict):
                        logger.warning(f"插件配置 {cfg_file} 顶层不是字典，跳过。")
                        continue
                    assistant_id = pdata.get("assistant_id")
                    if not assistant_id:
                        logger.warning(f"插件配置 {cfg_file} 缺少 assistant_id，跳过。")
                        continue
                    if "plugin_name" not in pdata or pdata["plugin_name"] != plugin_name:
                        pdata["plugin_name"] = plugin_name
                    if "name" not in pdata or not pdata["name"]:
                        pdata["name"] = plugin_name
                    mapping.setdefault(assistant_id, []).append(pdata)
                except Exception as e:
                    logger.error(f"读取插件实例文件 {cfg_file} 失败: {e}")
        return mapping

    def _load_workflows(self) -> list[dict]:
        """
        通过 WorkflowManager 读取所有工作流，返回列表(dict)。
        工作流的物理存储位于 config/workflows/*.json
        """
        try:
            wm = get_workflow_manager()
            return [w.model_dump() for w in wm.get_workflows()]
        except Exception as e:
            logger.error(f"加载工作流失败: {e}")
            return []

    def _assemble_settings(
        self,
        global_data: dict[str, Any],
        assistants_raw: dict[str, dict],
        plugin_map: dict[str, list[dict]],
        workflows: list[dict],
    ) -> dict[str, Any]:
        assistants: list[dict] = []
        for a_id, a_data in assistants_raw.items():
            a_copy = dict(a_data)
            plugin_list = plugin_map.get(a_id, [])
            a_copy["plugins"] = plugin_list
            assistants.append(a_copy)

        merged = dict(global_data)
        merged["assistants"] = assistants
        merged["workflows"] = workflows  # NEW
        return merged

    def _load_config(self) -> AppSettings:
        global_data = self._load_global_toml()
        assistants_raw = self._load_assistants()
        plugin_map = self._load_plugin_instances()
        workflows = self._load_workflows()  # NEW

        # 环境变量覆盖
        if "APP_DEFAULT_ASSISTANT" in os.environ:
            global_data["default_assistant"] = os.environ["APP_DEFAULT_ASSISTANT"]

        merged_data = self._assemble_settings(global_data, assistants_raw, plugin_map, workflows)

        try:
            return AppSettings.model_validate(merged_data)
        except ValidationError as e:
            logger.error(f"配置校验失败，使用占位默认: {e}")
            return AppSettings.model_validate(
                {
                    "llm": {
                        "model": "placeholder-model",
                        "provider": None,
                        "base_url": None,
                        "api_key": None,
                    },
                    "assistants": [],
                    "workflows": [],
                }
            )

    # =================== 保存逻辑 ===================
    def save_config(self) -> None:
        with self._lock:
            if not self._settings:
                logger.error("无 _settings，无法保存。")
                return

            data = self._settings.model_dump(mode="json", exclude_none=True)
            assistants = data.pop("assistants", [])
            # 不将 workflows 写入 dingent.toml（它们由 WorkflowManager 单独管理）
            workflows = data.pop("workflows", None)

            self._write_global_toml(data)
            self._write_assistants_and_plugins(assistants)

            log_with_context(
                "info",
                "Configuration saved (split-files)",
                context={
                    "global_config_path": str(self._global_config_path) if self._global_config_path else None,
                    "assistants_count": len(assistants),
                    "workflows_cached": len(workflows) if workflows else 0,
                },
                correlation_id="config_save_split",
            )

    def _write_global_toml(self, global_part: dict[str, Any]) -> None:
        if not self._global_config_path:
            logger.warning("未设置 global_config_path，跳过写入 dingent.toml。")
            return
        self._global_config_path.parent.mkdir(parents=True, exist_ok=True)
        if self._global_config_path.is_file():
            doc = tomlkit.parse(self._global_config_path.read_text("utf-8"))
        else:
            doc = tomlkit.document()
        doc.update(global_part)
        self._global_config_path.write_text(tomlkit.dumps(doc), "utf-8")

    def _write_assistants_and_plugins(self, assistants: list[dict]) -> None:
        if not self._assistants_dir or not self._plugins_dir:
            logger.warning("未初始化 assistants/plugins 目录，跳过写入。")
            return

        self._assistants_dir.mkdir(parents=True, exist_ok=True)
        self._plugins_dir.mkdir(parents=True, exist_ok=True)

        current_assistant_ids = set()
        desired_plugin_files: set[Path] = set()

        for a in assistants:
            a_id = a.get("id")
            if not a_id:
                logger.warning(f"发现缺少 id 的 assistant: {a.get('name')}，跳过保存其文件。")
                continue
            current_assistant_ids.add(a_id)

            a_copy = dict(a)
            plugin_list = a_copy.pop("plugins", [])

            assistant_file = self._assistants_dir / f"{a_id}.yaml"
            with assistant_file.open("w", encoding="utf-8") as f:
                yaml.safe_dump(a_copy, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            for p in plugin_list:
                p_copy = dict(p)
                p_copy["assistant_id"] = a_id
                plugin_name = p_copy.get("plugin_name") or p_copy.get("name")
                if not plugin_name:
                    logger.warning(f"插件实例缺少 plugin_name/name 字段，assistant {a_id} 跳过: {p}")
                    continue
                target_dir = self._plugins_dir / plugin_name
                target_dir.mkdir(parents=True, exist_ok=True)
                plugin_file = target_dir / f"{a_id}.yaml"
                desired_plugin_files.add(plugin_file)
                with plugin_file.open("w", encoding="utf-8") as pf:
                    yaml.safe_dump(
                        p_copy,
                        pf,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                    )

        for old_file in self._assistants_dir.glob("*.yaml"):
            try:
                if old_file.stem not in current_assistant_ids:
                    old_file.unlink()
            except Exception as e:
                logger.error(f"删除过期助理文件 {old_file} 失败: {e}")

        for plugin_dir in self._plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            for cfg_file in plugin_dir.glob("*.yaml"):
                if cfg_file not in desired_plugin_files:
                    try:
                        cfg_file.unlink()
                    except Exception as e:
                        logger.error(f"删除过期插件实例文件 {cfg_file} 失败: {e}")
            try:
                if not any(plugin_dir.iterdir()):
                    plugin_dir.rmdir()
            except Exception:
                pass

    # =================== 公共 API ===================
    def get_config(self) -> AppSettings:
        with self._lock:
            return self._settings.model_copy(deep=True)

    def reload(self) -> None:
        with self._lock:
            self._settings = self._load_config()
            logger.info("配置已重新加载。")

    def update_config(self, new_config_data: dict[str, Any], override_empty=False) -> None:
        if not isinstance(new_config_data, dict):
            raise TypeError("new_config_data must be a dict")
        with self._lock:
            try:
                cleaned = new_config_data if override_empty else _clean_patch(new_config_data)
                if not cleaned:
                    logger.debug("更新跳过：清洗后为空。")
                    return
                current_data = self._settings.model_dump()
                merged = deep_merge(current_data, cleaned, ["id", "name"])
                new_settings = AppSettings.model_validate(merged)
                self._settings = new_settings
                self.save_config()
            except ValidationError as e:
                raise ConfigUpdateError(f"Configuration validation failed: {e}") from e

    def get_all_assistants_config(self) -> dict[str, Any]:
        with self._lock:
            return {a.id: a for a in self._settings.assistants}

    def get_assistant_by_id(self, assistant_id: str) -> AssistantSettings | None:
        with self._lock:
            return next((a for a in self._settings.assistants if a.id == assistant_id), None)

    def get_assistant_by_name(self, assistant_name: str) -> AssistantSettings | None:
        with self._lock:
            return next((a for a in self._settings.assistants if a.name == assistant_name), None)

    def add_assistant(self, assistant: AssistantCreate) -> None:
        with self._lock:
            if self.get_assistant_by_name(assistant.name):
                raise ValueError(f"Assistant name '{assistant.name}' already exists.")
            assistant_settings = AssistantSettings.model_validate(assistant.model_dump())
            self._settings.assistants.append(assistant_settings)
            self.save_config()

    def remove_assistant(self, assistant_id: str) -> None:
        with self._lock:
            before = len(self._settings.assistants)
            self._settings.assistants = [a for a in self._settings.assistants if a.id != assistant_id]
            after = len(self._settings.assistants)
            if before == after:
                raise AssistantNotFoundError(f"Assistant '{assistant_id}' not found.")
            if self._assistants_dir:
                afile = self._assistants_dir / f"{assistant_id}.yaml"
                if afile.is_file():
                    try:
                        afile.unlink()
                    except Exception as e:
                        logger.error(f"删除助理文件失败 {afile}: {e}")
            if self._plugins_dir and self._plugins_dir.is_dir():
                for pdir in self._plugins_dir.iterdir():
                    if not pdir.is_dir():
                        continue
                    inst_file = pdir / f"{assistant_id}.yaml"
                    if inst_file.is_file():
                        try:
                            inst_file.unlink()
                        except Exception as e:
                            logger.error(f"删除插件实例文件失败 {inst_file}: {e}")
                    try:
                        if not any(pdir.iterdir()):
                            pdir.rmdir()
                    except Exception:
                        pass
            self.save_config()

    # ============ 插件操作 ============
    def add_plugin_config_to_assistant(self, assistant_id: str, plugin_name: str) -> None:
        plugin_manager = get_plugin_manager()
        plugin_manifest = plugin_manager.get_plugin_manifest(plugin_name)
        if not plugin_manifest:
            raise ValueError(f"Plugin '{plugin_name}' 未注册或不存在。")

        with self._lock:
            assistant = self.get_assistant_by_id(assistant_id)
            if not assistant:
                raise AssistantNotFoundError(f"Assistant '{assistant_id}' not found.")

            if any(p.plugin_name == plugin_name for p in assistant.plugins):
                raise ValueError(f"Plugin '{plugin_name}' 已存在于助手 '{assistant.name}'。")

            new_plugin_config = PluginUserConfig(
                name=plugin_name,
                plugin_name=plugin_name,
                enabled=True,
                tools_default_enabled=True,
                config={},
                tools=[],
            )
            assistant.plugins.append(new_plugin_config)
            self.save_config()

            log_with_context(
                "info",
                "Plugin added",
                context={
                    "plugin_name": plugin_name,
                    "assistant_id": assistant_id,
                    "assistant_name": assistant.name,
                },
                correlation_id=f"plugin_add_{plugin_name}_{assistant_id}",
            )

    def remove_plugin_from_assistant(self, assistant_id: str, plugin_name: str) -> None:
        with self._lock:
            assistant = self.get_assistant_by_id(assistant_id)
            if not assistant:
                raise AssistantNotFoundError(f"Assistant '{assistant_id}' not found.")

            target = None
            for p in assistant.plugins:
                if p.plugin_name == plugin_name or p.name == plugin_name:
                    target = p
                    break
            if not target:
                raise ValueError(f"Assistant '{assistant.name}' 未配置插件 '{plugin_name}'。")

            assistant.plugins.remove(target)

            if self._plugins_dir:
                plugin_dir = self._plugins_dir / plugin_name
                inst_file = plugin_dir / f"{assistant_id}.yaml"
                if inst_file.is_file():
                    try:
                        inst_file.unlink()
                    except Exception as e:
                        logger.error(f"删除插件实例文件失败 {inst_file}: {e}")
                try:
                    if plugin_dir.is_dir() and not any(plugin_dir.iterdir()):
                        plugin_dir.rmdir()
                except Exception:
                    pass

            self.save_config()
            logger.success(f"已从助手 '{assistant.name}' 移除插件 '{plugin_name}'。")

    def remove_plugin_globally(self, plugin_name: str) -> None:
        with self._lock:
            changed = False
            for assistant in self._settings.assistants:
                original_len = len(assistant.plugins)
                assistant.plugins = [p for p in assistant.plugins if not (p.plugin_name == plugin_name or p.name == plugin_name)]
                if len(assistant.plugins) != original_len:
                    changed = True

            if self._plugins_dir:
                plugin_dir = self._plugins_dir / plugin_name
                if plugin_dir.is_dir():
                    for f in plugin_dir.glob("*.yaml"):
                        try:
                            f.unlink()
                        except Exception as e:
                            logger.error(f"删除文件失败 {f}: {e}")
                    try:
                        plugin_dir.rmdir()
                    except Exception as e:
                        logger.error(f"删除目录失败 {plugin_dir}: {e}")

            if changed:
                self.save_config()
                logger.success(f"插件 '{plugin_name}' 全局删除完成。")
            else:
                logger.info(f"没有任何助理使用插件 '{plugin_name}'。")

    def update_assistant(self, assistant_id: str, updated_data: AssistantUpdate) -> None:
        with self._lock:
            assistant = self.get_assistant_by_id(assistant_id)
            if not assistant:
                raise AssistantNotFoundError(f"Assistant '{assistant_id}' not found.")
            raw = assistant.model_dump()
            patch = {k: v for k, v in updated_data.model_dump(exclude_unset=True).items() if v is not None}
            merged = deep_merge(raw, patch, ["id", "name"])
            new_assistant = AssistantSettings.model_validate(merged)

            for i, a in enumerate(self._settings.assistants):
                if a.id == assistant_id:
                    self._settings.assistants[i] = new_assistant
                    break
            self.save_config()

    def get_current_workflow(self):
        with self._lock:
            workflow_manager = get_workflow_manager()
            workflow_id = self._settings.current_workflow
            workflow = workflow_manager.get_workflow(str(workflow_id))
            if not workflow and self._settings.workflows:
                workflows = workflow_manager.get_workflows()
                workflow = workflows[0] if workflows else None
            if not workflow:
                raise ValueError("No workflow available.")
            return workflow


config_manager: ConfigManager | None = None


def get_config_manager():
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager
