import importlib
import sys
from pathlib import Path
from typing import Any

import toml
from loguru import logger
from pydantic import BaseModel, ValidationError

from dingent.engine.plugins.base import BaseTool
from dingent.utils import find_project_root


class PluginManager:
    def __init__(self, plugin_dir: str | None = None, global_injection_deps: dict | None = None):
        if not plugin_dir:
            project_root = find_project_root()
            if project_root:
                self.plugin_dir = project_root / "assistants" / "plugins"
            else:
                self.plugin_dir = None
        else:
            self.plugin_dir = Path(plugin_dir)
        if self.plugin_dir:
            plugin_root_path = str(self.plugin_dir.resolve())
            if plugin_root_path not in sys.path:
                sys.path.insert(0, plugin_root_path)
            self._plugins = {}
            print(f"Initializing PluginManager, scanning directory: '{self.plugin_dir}'")
            self._scan_and_register_plugins()
            self.global_injection_deps = global_injection_deps
            sys.path.pop(0)

    def _scan_and_register_plugins(self):
        if not self.plugin_dir.is_dir():
            print(f"Warning: Plugin directory '{self.plugin_dir}' not found.")
            return

        for plugin_path in self.plugin_dir.iterdir():
            if not plugin_path.is_dir():
                logger.warning(f"Skipping '{plugin_path}' as it is not a directory.")
                continue

            toml_path = plugin_path / "plugin.toml"
            if not toml_path.is_file():
                logger.warning(f"Skipping '{plugin_path}' as 'plugin.toml' is missing.")
                continue

            try:
                plugin_info = toml.load(toml_path)
                plugin_meta = plugin_info.get("plugin", {})
                tool_name = plugin_meta.get("name")
                tool_class_str = plugin_meta.get("tool_class")
                dependencies = plugin_meta.get("dependencies", {})

                if not tool_name or not tool_class_str:
                    logger.warning(f"Warning: Skipping plugin in '{plugin_path}'. 'name' or 'tool_class' missing.")
                    continue

                # 2. 动态加载 Pydantic 配置模型
                plugin_pkg_name = plugin_path.name
                settings_model = None
                try:
                    # 现在可以使用标准的绝对路径导入
                    settings_module = importlib.import_module(f"{plugin_pkg_name}.settings")
                    settings_model = getattr(settings_module, "Settings", None)
                    sys.path.pop(0)
                    if not settings_model or not issubclass(settings_model, BaseModel):
                        settings_model = None
                except ImportError:
                    pass  # settings.py 是可选的

                module_name, class_name = tool_class_str.split(":")
                tool_module = importlib.import_module(f"{plugin_pkg_name}.{module_name}")
                tool_class = getattr(tool_module, class_name, None)
                sys.path.pop(0)

                if not tool_class:
                    print(f"Warning: Skipping plugin '{tool_name}'. Class '{class_name}' not found.")
                    continue

                # register the plugin
                self._plugins[tool_name] = {
                    "name": tool_name,
                    "path": plugin_path,
                    "config_model": settings_model,
                    "dependencies": dependencies,
                    "tool_class": tool_class,
                    "meta": plugin_meta,
                }
                print(f"Successfully registered plugin: '{tool_name}'")

            except Exception as e:
                print(f"Error loading plugin from '{plugin_path}': {e}")

    def get_registered_plugins(self) -> dict[str, Any]:
        return self._plugins

    def load_plugin(self, tool_name: str, injection_deps: dict[str, Any] | None = None) -> BaseTool:
        if tool_name not in self._plugins:
            raise ValueError(f"Plugin '{tool_name}' is not registered or failed to load.")

        plugin_data = self._plugins[tool_name]
        injection_deps = injection_deps.copy() if injection_deps else {}
        injection_deps.update(self.global_injection_deps or {})

        ConfigModel = plugin_data.get("config_model")
        if ConfigModel:
            user_config = injection_deps.get("config", {})
            try:
                # 使用用户提供的字典来实例化 Pydantic 模型
                # Pydantic 会自动合并默认值、校验类型和规则
                config_instance = ConfigModel.model_validate(user_config.model_dump())
                injection_deps["config"] = config_instance  # 注入 Pydantic 对象
            except ValidationError as e:
                print(f"Error validating configuration for plugin '{tool_name}': {e}")
                raise ValueError(f"Invalid configuration for {tool_name}.") from e

        ToolClass = plugin_data["tool_class"]

        try:
            instance = ToolClass(**injection_deps)
            return instance
        except TypeError as e:
            print(f"Error instantiating plugin '{tool_name}'. Check its __init__ method signature.")
            raise e
