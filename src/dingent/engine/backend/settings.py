from functools import lru_cache
from pathlib import Path

import toml
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict

from dingent.engine.backend.types import AssistantSettings
from dingent.utils import find_project_root


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    assistants: list[AssistantSettings] = []
    default_assistant: str | None = None
    llm: dict[str, str | int] = {}


@lru_cache
def get_settings() -> AppSettings:
    project_root: Path | None = find_project_root()
    if not project_root:
        logger.warning("Project root not found. Using default settings.")
        return AppSettings()
    user_config_path = project_root / "backend" / "config.toml"
    if user_config_path.is_file():
        logger.info(f"Loading user config from: {user_config_path}")
        user_data = toml.load(user_config_path)
    else:
        user_data = {}

    return AppSettings(**user_data)
