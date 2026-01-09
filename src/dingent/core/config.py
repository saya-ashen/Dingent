from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from dingent.core.paths import paths


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(paths.env_file), env_file_encoding="utf-8", extra="ignore")

    # --- 基础配置 ---
    PROJECT_NAME: str = "Dingent"

    DING_MASTER_KEY: str | None = None

    DATABASE_URL: str = f"sqlite:///{paths.sqlite_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
