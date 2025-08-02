import importlib
import importlib.resources
import inspect
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from loguru import logger

from ..tools.base_tool import BaseTool
from .settings import ToolSettings


class ToolManager:
    def __init__(self, di_container: dict):
        self.di_container = di_container
        self._tool_classes: dict[str, type[Any]] = {}  # Use 'Any' or your BaseTool type
        self._tool_instances: dict[str, Any] = {}

    def load_tools(self, tools_settings: list[ToolSettings], custom_tool_dirs: list[str | Path] | None = None):
        """
        Loads tools specified in the settings from built-in and custom directories.
        """
        print("🛠️  Initializing tool loading process based on settings...")

        # 1. Prepare a list of all locations to search for tools
        search_locations = []
        # Add built-in tools directory
        try:
            built_in_path = importlib.resources.files("dingent.engine.mcp") / "tools" / "built_in"
            if built_in_path.is_dir():
                search_locations.append({"path": Path(built_in_path), "prefix": "dingent.engine.mcp.tools.built_in", "is_custom": False})
                logger.debug(f"-> Preparing to search built-in tools at: {built_in_path}")
        except (ModuleNotFoundError, FileNotFoundError):
            print("-> Warning: Could not find built-in tools directory.")
        # Add any custom tool directories
        if custom_tool_dirs:
            for directory in custom_tool_dirs:
                custom_path = Path(directory).resolve()
                if custom_path.is_dir():
                    search_locations.append({"path": custom_path, "prefix": "", "is_custom": True})
                    logger.debug(f"-> Preparing to search custom tools at: {custom_path}")
                else:
                    logger.debug(f"-> Warning: Custom tool directory not found, skipping: {custom_path}")

        # 2. Iterate through settings and load each enabled tool
        for setting in tools_settings:
            if not setting.enabled:
                logger.debug(f"-> Tool '{setting.name}' is disabled, skipping.")
                continue

            logger.debug(f"-> Attempting to load tool '{setting.name}'...")
            self._find_and_register_tool(setting, search_locations)

        logger.debug(f"✅ Tool loading complete. {len(self._tool_classes)} total tool classes registered.")

    def _find_and_register_tool(self, setting: ToolSettings, search_locations: list[dict]):
        """
        Finds and registers a single tool based on its settings by searching all known locations.
        """
        tool_name = setting.name

        for loc in search_locations:
            path_as_file = loc["path"] / f"{tool_name}.py"
            path_as_dir = loc["path"] / tool_name

            module_to_load = None
            if path_as_file.is_file():
                module_to_load = tool_name
            elif path_as_dir.is_dir() and (path_as_dir / "tool.py").is_file():
                module_to_load = f"{tool_name}.tool"

            # If we found a potential module, try to import and register it
            if module_to_load:
                if self._import_and_register(setting, module_to_load, loc):
                    return  # Success, stop searching for this tool

        # If the loop completes without returning, the tool was not found
        print(f"-> ❌ Warning: Could not find a loadable file/directory for enabled tool '{tool_name}' in any location.")

    def _import_and_register(self, setting: ToolSettings, module_to_load: str, location_info: dict) -> bool:
        """
        Handles the import, class retrieval, and registration for a found tool module.
        Returns True on success, False on failure.
        """
        full_module_name = f"{location_info['prefix']}.{module_to_load}" if location_info["prefix"] else module_to_load

        path_to_add = str(location_info["path"]) if location_info["is_custom"] else None
        path_was_added = False

        try:
            # Temporarily add custom tool paths to sys.path for the import
            if path_to_add and path_to_add not in sys.path:
                sys.path.insert(0, path_to_add)
                path_was_added = True

            module = importlib.import_module(full_module_name)
            tool_class = None

            # MODIFICATION START: Auto-detect class if not specified
            if setting.class_name:
                # If a class name is specified, find it directly.
                tool_class = getattr(module, setting.class_name, None)
            else:
                # If no class name, find the first valid BaseTool subclass in the module.
                print(f"  -> No class_name specified. Auto-detecting tool in '{full_module_name}'...")
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseTool) and obj is not BaseTool:
                        tool_class = obj
                        # We can optionally update the setting object with the found class name
                        setting.class_name = name
                        print(f"  -> Auto-detected tool class: '{name}'")
                        break  # Stop after finding the first one
            # MODIFICATION END

            if not tool_class:
                if setting.class_name:
                    print(f"  -> Error: Class '{setting.class_name}' not found in module '{full_module_name}'.")
                else:
                    print(f"  -> Error: No valid BaseTool subclass found in module '{full_module_name}'.")
                return False

            if issubclass(tool_class, BaseTool) and tool_class is not BaseTool:
                self._tool_classes[setting.name] = tool_class
                print(f"  -> ✅ Registered '{setting.name}' from {full_module_name}")
                return True
            else:
                print(f"  -> Error: Class '{setting.class_name}' is not a valid tool.")
                return False

        except Exception as e:
            print(f"  -> Error importing or registering tool from '{full_module_name}': {e}")
            return False
        finally:
            # Clean up sys.path if it was modified
            if path_was_added and path_to_add in sys.path:
                sys.path.remove(path_to_add)

    @staticmethod
    def _get_all_constructor_params(cls: type) -> OrderedDict[str, inspect.Parameter]:
        """
        Inspects a class and its entire inheritance hierarchy (MRO)
        to collect all unique __init__ parameters.
        """
        all_params = OrderedDict()
        # Iterate over the Method Resolution Order (MRO) from the class to its ancestors
        for base_class in cls.mro():
            # Skip the top-level 'object' class
            if base_class is object:
                continue

            # Get the signature of the __init__ method for the current class in the hierarchy
            try:
                signature = inspect.signature(base_class.__init__)
                for param in signature.parameters.values():
                    # Filter out 'self', '*args', and '**kwargs'
                    if param.name in ("self", "cls") or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                        continue

                    # Add the parameter if it hasn't been seen yet.
                    # This ensures we get all unique dependencies from the entire chain.
                    if param.name not in all_params:
                        all_params[param.name] = param
            except (ValueError, TypeError):
                # Some built-in types might not have a retrievable signature
                continue
        return all_params

    def _get_instance(self, tool_name: str) -> Any:  # BaseTool
        # This dependency injection logic remains unchanged.
        if tool_name in self._tool_instances:
            return self._tool_instances[tool_name]

        if tool_name not in self._tool_classes:
            raise ValueError(f"Tool '{tool_name}' is not registered.")

        tool_class = self._tool_classes[tool_name]
        init_params = self._get_all_constructor_params(tool_class)

        logger.info(f"🛠️  Resolving dependencies for tool '{tool_name}': {list(init_params.keys())}")

        dependencies = {}
        for param_name, param in init_params.items():
            if param_name == "self":
                continue

            dependency_found = self.di_container.get(param_name, None)
            if dependency_found is None:
                dependency_found = self.di_container.get(param.annotation)

            if dependency_found or param_name in self.di_container.keys() or param.annotation in self.di_container.keys():
                dependencies[param_name] = dependency_found
            else:
                error_msg = f"Cannot satisfy dependency '{param_name}:{param.annotation}' for tool '{tool_name}'."
                logger.error(error_msg)
                raise TypeError(error_msg)

        instance = tool_class(**dependencies)
        self._tool_instances[tool_name] = instance
        return instance

    def load_mcp_tool(self, tool_name: str):
        try:
            instance = self._get_instance(tool_name)
            return instance.tool_run
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Error loading tool '{tool_name}': {e}")
            return None
