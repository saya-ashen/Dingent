import importlib.resources
import os
from functools import lru_cache
from pathlib import Path

import toml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ToolSettings(BaseModel):
    name: str
    enabled: bool = True
    icon: str | None = None
    description: str
    class_name: str | None = Field(None, alias="class")
    exclude_args: list[str] = []


class MCPSettings(BaseModel):
    name: str
    icon: str | None = None
    llm: dict[str, str]
    database: str | None = None
    enabled_tools: list[str] = []
    description: str
    host: str
    port: int


class DatabaseSettings(BaseModel):
    name: str
    uri: str = ""
    uri_env: str = ""
    schemas_file: str | None = None
    type: str | None = None

    @model_validator(mode="after")
    def determine_type_from_uri(self) -> "DatabaseSettings":
        """
        Runs after all fields are populated to ensure `uri` is available.
        """
        db_uri = self.uri
        if not db_uri:
            if self.uri_env and self.uri_env in os.environ:
                db_uri = os.environ[self.uri_env]
                self.uri = db_uri

        if not db_uri:
            raise ValueError("A database URI must be provided either via 'uri' field or 'uri_env' environment variable.")

        if db_uri.startswith("postgresql"):
            self.type = "postgresql"
        elif db_uri.startswith("mysql"):
            self.type = "mysql"
        elif db_uri.startswith("sqlite"):
            self.type = "sqlite"
        else:
            raise ValueError(f"Could not determine database type from URI: '{db_uri[:30]}...'")

        return self


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    databases: list[DatabaseSettings] = []
    mcp_servers: list[MCPSettings] = []
    tools: list[ToolSettings] = []
    custom_tools_dirs: list[Path] = Field(default=[Path("custom_tools")], alias="MYAPP_CUSTOM_TOOLS_DIRS")
    custom_schemas_dirs: list[Path] = []
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
