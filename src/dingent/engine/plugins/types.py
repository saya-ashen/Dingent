from typing import Literal, TypeVar

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class BasePluginSettings(BaseSettings):
    """
    Developer should inherit this class to define user-specific plugin configuration.
    """

    model_config = SettingsConfigDict(extra="allow")
    name: str
    plugin_name: str


class ExecutionModel(BaseModel):
    """定义插件的运行方式"""

    mode: Literal["local", "remote"] = Field(..., description="运行模式: 'local' 或 'remote'")

    url: str | None = None
    script_path: str | None = Field(None, description="插件管理器需要运行的Python入口文件路径")
    mcp_json_path: str | None = None

    @model_validator(mode="after")
    def check_exclusive_execution_mode(self) -> "ExecutionModel":
        """校验器：确保 'local' 和 'remote' 配置与 'mode' 字段匹配"""
        return self


class ToolConfigModel(BaseModel):
    """用户个性化配置的定义"""

    schema_path: FilePath = Field(..., description="指向一个包含用户配置Pydantic类的Python文件")


class PluginSettings(BaseSettings):
    """ """

    name: str = Field(..., description="插件的唯一标识符")
    version: str | float = Field("0.2.0", description="插件版本 (遵循语义化版本)")
    spec_version: str | float = Field("2.0", description="插件规范版本 (遵循语义化版本)")
    description: str
    execution: ExecutionModel
    dependencies: list[str] | None = None
    python_version: str | None = None


def export_settings_to_env_dict(settings: BaseSettings) -> dict[str, str]:
    """
    export settings to a flat dictionary suitable for environment variables.
    """
    # 获取配置元信息
    config = settings.model_config
    prefix = config.get("env_prefix", "")
    delimiter = config.get("env_nested_delimiter") or "__"

    # 使用 model_dump 获取原始数据字典
    data = settings.model_dump()

    env_vars = {}

    def flatten_dict(d: dict, current_prefix: str = ""):
        for key, value in d.items():
            # 构建环境变量的键
            new_key = (current_prefix + key).upper()
            if isinstance(value, dict):
                # 如果是嵌套字典，递归处理
                flatten_dict(value, current_prefix=f"{new_key}{delimiter}")
            elif isinstance(value, list | tuple):
                # Pydantic v2 默认将列表/元组转为 JSON 字符串
                # 这也是环境变量传递复杂结构的常用方式
                env_vars[new_key] = str(value)
            elif isinstance(value, bool):
                # 将布尔值转为小写的 'true'/'false'
                env_vars[new_key] = str(value).lower()
            else:
                # 其他类型直接转为字符串
                env_vars[new_key] = str(value)

    flatten_dict(data, current_prefix=prefix)
    return env_vars
