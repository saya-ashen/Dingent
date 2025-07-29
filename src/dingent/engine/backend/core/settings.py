from functools import lru_cache
from pathlib import Path

import toml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerInfo(BaseModel):
    name: str
    host: str
    port: int
    routable_nodes: list[str] = []


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",env_file_encoding="utf-8", extra="ignore")
    mcp_servers: list[MCPServerInfo] = []
    default_agent:str|None = None
    llm: dict[str, str]



@lru_cache
def get_settings() -> AppSettings:
    """
    加载、合并并返回最终的配置对象。
    此过程只执行一次。
    """
    user_config_path = Path.cwd() / "config.toml"
    if user_config_path.is_file():
        print(f"Loading user config from: {user_config_path}")
        user_data = toml.load(user_config_path)
    else:
        user_data = {}

    return AppSettings(**user_data)
