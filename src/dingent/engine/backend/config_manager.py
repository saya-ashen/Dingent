from __future__ import annotations

from threading import RLock
from typing import Any

from pydantic import ValidationError

from .settings import AppSettings

# 说明：
# - 假设 AppSettings 是一个 Pydantic v2 的模型，具备 .model_dump() 和 .save() 方法
# - 且包含属性 assistants（列表），列表元素具备 name 字段


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

    def __new__(cls, *args, **kwargs):
        # 实现单例模式，确保全局只有一个实例
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if getattr(self, "_initialized", False):
            return
        with self._lock:
            if self._settings is None:
                # 这里假定 AppSettings 可无参构造
                self._settings = AppSettings()  # type: ignore[name-defined]
            self._initialized = True

    # ===================== 对外 API =====================

    def save_config(self) -> None:
        """将当前内存中的配置保存到文件"""
        with self._lock:
            self._settings.save()

    def get_config(self) -> AppSettings:  # type: ignore[name-defined]
        """安全地获取当前配置"""
        with self._lock:
            return self._settings

    def update_config(self, new_config_data: dict[str, Any]) -> dict[str, Any]:
        """
        核心方法：实时更新配置。
        它会：
        1) 将新数据与当前配置字典进行深度合并（右侧覆盖左侧）。
        2) 使用合并后的数据重新构建 AppSettings 实例（让 Pydantic 做校验）。
        3) 保存到文件。

        返回:
            {"success": True} 或 {"success": False, "error": "..."}
        """
        if not isinstance(new_config_data, dict):
            return {"success": False, "error": "new_config_data 必须为字典"}

        with self._lock:
            try:
                # 取出当前配置的字典表示
                current_data = self._settings.model_dump()  # 依赖 Pydantic v2
                # 深度合并
                merged = self._deep_merge(current_data, new_config_data)
                # 构建新配置（校验）
                new_settings = AppSettings(**merged)  # type: ignore[name-defined]
                # 写回内存并保存
                self._settings = new_settings
                self._settings.save()
                return {"success": True}
            except ValidationError as e:
                return {"success": False, "error": str(e)}

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

    def get_assistant_config(self, assistant_name: str):
        """根据名称获取单个 assistant 配置对象（Pydantic 实例），找不到返回 None"""
        with self._lock:
            assistants = getattr(self._settings, "assistants", []) or []
            for assistant in assistants:
                if getattr(assistant, "name", None) == assistant_name:
                    return assistant
            return None

    def get_all_assistants_config(self) -> dict[str, Any]:
        """返回一个 name -> assistant 对象 的映射字典"""
        with self._lock:
            assistants = getattr(self._settings, "assistants", []) or []
            return {getattr(a, "name", None): a for a in assistants if getattr(a, "name", None)}

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
