import importlib.resources
from functools import lru_cache
from pathlib import Path

import toml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from dingent.engine.plugins import BaseSettings as ToolBaseSettings


class AssistantSettings(BaseModel):
    name: str
    icon: str | None = None
    tools: list[ToolBaseSettings] = []
    description: str
    host: str
    port: int


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    assistants: list[AssistantSettings] = []
    log_level: str = "INFO"
    log_sink: str = "logs/backend.log"


def merge_configs(base: dict, user: dict) -> dict:
    """
    Merge two configuration dictionaries intelligently.
    """
    merged = base.copy()

    if "tools" in user:
        if "tools" not in merged:
            merged["tools"] = []

        base_tools_map = {tool["id"]: tool for tool in merged["tools"]}
        for user_tool in user["tools"]:
            tool_id = user_tool.get("id")
            if tool_id:
                base_tools_map[tool_id] = user_tool
        merged["tools"] = list(base_tools_map.values())

    for key, value in user.items():
        if key != "tools":
            merged[key] = value

    return merged


@lru_cache
def get_settings() -> AppSettings:
    base_data = {}

    try:
        traversable = importlib.resources.files("dingent.engine.mcp.resources").joinpath("default_settings.toml")
        with importlib.resources.as_file(traversable) as default_config_path:
            print(f"Loading built-in config from: {default_config_path}")
            base_data = toml.load(default_config_path)

    except (ModuleNotFoundError, FileNotFoundError):
        print("Warning: Built-in default_settings.toml not found. Proceeding with empty base config.")
        base_data = {}

    user_config_path = Path.cwd() / "config.toml"
    if user_config_path.is_file():
        print(f"Loading user config from: {user_config_path}")
        user_data = toml.load(user_config_path)
    else:
        user_data = {}

    merged_data = merge_configs(base_data, user_data)

    return AppSettings(**merged_data)
