from functools import lru_cache
from pathlib import Path

import toml
from loguru import logger
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AssistantInfo(BaseModel):
    name: str
    host: str
    port: int
    routable_nodes: list[str] = []


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    assistants: list[AssistantInfo] = []
    default_assistant: str | None = None
    llm: dict[str, str] = {}


@lru_cache
def get_settings() -> AppSettings:
    user_config_path = Path.cwd() / "config.toml"
    if user_config_path.is_file():
        logger.info(f"Loading user config from: {user_config_path}")
        user_data = toml.load(user_config_path)
    else:
        user_data = {}

    return AppSettings(**user_data)
