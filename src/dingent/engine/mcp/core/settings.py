import importlib.resources
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import toml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseModel):
    name: str 
    provider: str 
    base_url:str = "https://www.dmxapi.cn/v1"
    api_key: str|None = None


class ToolSettings(BaseModel):
    name: str
    enabled: bool = True
    icon: str
    description: str
    class_name: str | None = Field(None, alias="class")  # 使用 alias 来处理 'class' 这个 Python 关键字
    exclude_args: list[str] = []


class MCPSettings(BaseModel):
    name: str
    icon: str
    llm: dict[str, str]
    database: str | None = None
    enabled_tools: list[str] = []
    description:str
    host:str
    port:int


class DatabaseSettings(BaseModel):
    name: str
    uri: str = ""
    uri_env: str = ""
    schemas_file: str
    type: Literal["mysql", "postgresql"] | None = None

    @model_validator(mode="after")
    def determine_type_from_uri(self) -> "DatabaseSettings":
        """
        在字段填充后运行此验证器，以根据 URI 确定数据库类型。
        """
        # 步骤 1: 获取 URI 字符串
        db_uri = self.uri
        if not db_uri:
            if self.uri_env and self.uri_env in os.environ:
                db_uri = os.environ[self.uri_env]
                # 将从环境变量中获取的 URI 也设置到模型的 uri 字段上，保持一致性
                self.uri = db_uri

        if not db_uri:
            raise ValueError(
                "A database URI must be provided either via 'uri' field or 'uri_env' environment variable."
            )

        # 步骤 2: 推断类型
        if db_uri.startswith("postgresql"):
            self.type = "postgresql"
        elif db_uri.startswith("mysql"):
            self.type = "mysql"
        else:
            raise ValueError(f"Could not determine database type from URI: '{db_uri[:30]}...'")

        # 步骤 3: 返回更新后的模型实例
        return self


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")
    databases: list[DatabaseSettings] = []
    llms: list[LLMSettings] = []
    mcp_servers: list[MCPSettings] = []
    tools: list[ToolSettings] = []
    custom_tools_dirs: list[Path] = Field(default=[], alias="MYAPP_CUSTOM_TOOLS_DIRS")
    custom_schemas_dirs: list[Path] = []


def merge_configs(base: dict, user: dict) -> dict:
    """
    合并两个配置字典。
    - 对 'tools' 列表进行智能合并（基于 'id'）。
    - 对所有其他项，用户配置覆盖基础配置。
    """
    merged = base.copy()

    # 智能合并 'tools'
    if "tools" in user:
        # 如果基础配置中没有 'tools'，则创建一个空列表
        if "tools" not in merged:
            merged["tools"] = []

        base_tools_map = {tool["id"]: tool for tool in merged["tools"]}
        for user_tool in user["tools"]:
            tool_id = user_tool.get("id")
            if tool_id:
                base_tools_map[tool_id] = user_tool  # 覆盖或添加
        merged["tools"] = list(base_tools_map.values())

    # 其他所有配置：用户配置直接覆盖
    for key, value in user.items():
        if key != "tools":
            merged[key] = value

    return merged


@lru_cache
def get_settings() -> AppSettings:
    """
    加载、合并并返回最终的配置对象。
    此过程只执行一次。
    """
    base_data = {}

    # --- 1. 定位并加载内置的默认配置 (使用 importlib.resources) ---
    try:
        # 'my_awesome_tool.resources' 是包含资源的包的 Python 路径
        # .joinpath() 用于附加文件名
        # .as_file() 是一个上下文管理器，它能确保我们得到一个真实的文件系统路径
        # （如果资源在 zip 中，它会临时解压出来）
        traversable = importlib.resources.files("mcp_servers.resources").joinpath("default_settings.toml")
        with importlib.resources.as_file(traversable) as default_config_path:
            print(f"Loading built-in config from: {default_config_path}")
            base_data = toml.load(default_config_path)

    except (ModuleNotFoundError, FileNotFoundError):
        # 如果包或文件不存在，则静默处理，使用空配置
        print("Warning: Built-in default_settings.toml not found. Proceeding with empty base config.")
        base_data = {}

    # --- 2. 加载用户的自定义配置 ---
    # 用户的配置文件总是在文件系统中，所以可以直接使用 Path
    user_config_path = Path.cwd() / "config.toml"
    if user_config_path.is_file():
        print(f"Loading user config from: {user_config_path}")
        user_data = toml.load(user_config_path)
    else:
        user_data = {}

    # --- 3. 合并 ---
    merged_data = merge_configs(base_data, user_data)

    # --- 4. 实例化并返回 ---
    return AppSettings(**merged_data)
