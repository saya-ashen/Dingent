from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dingent.core.paths import paths  # 导入上面的 paths


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(paths.env_file), env_file_encoding="utf-8", extra="ignore")

    # --- 基础配置 ---
    PROJECT_NAME: str = "dingent"
    ENVIRONMENT: str = "development"

    # 使用 paths 中的路径作为默认值
    DATABASE_URL: str = f"sqlite:///{paths.sqlite_path}"

    DINGENT_MASTER_KEY: SecretStr

    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
