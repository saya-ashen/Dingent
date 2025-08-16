from typing import Any, Literal, TypeVar

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    model_validator,
)

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class ConfigItemDetail(BaseModel):
    """Represents a single configuration item with its schema and value."""

    name: str = Field(..., description="配置项的名称 (环境变量名)")
    type: str = Field(..., description="配置项的期望类型 (e.g., 'string', 'number')")
    required: bool = Field(..., description="是否为必需项")
    secret: bool = Field(False, description="是否为敏感信息 (如 API Key)")
    description: str | None = Field(None, description="该配置项的描述")
    default: Any | None = Field(None, description="默认值 (如果存在)")
    value: Any | None = Field(None, description="用户设置的当前值")


class PluginConfigSchema(BaseModel):
    name: str
    type: Literal["string", "float", "integer", "bool"]
    required: bool = True
    secret: bool = False
    default: str | int | float | None = None
    description: str | None = None


class ToolOverrideConfig(BaseModel):
    name: str
    enabled: bool = True
    description: str | None = None


class PluginUserConfig(BaseModel):
    """
    Developer should inherit this class to define user-specific plugin configuration.
    """

    name: str
    plugin_name: str
    tools_default_enabled: bool = True
    enabled: bool = True
    tools: list[ToolOverrideConfig] | None = None
    config: dict | None = None


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


def export_settings_to_env_dict(settings: BaseModel) -> dict[str, str]:
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
