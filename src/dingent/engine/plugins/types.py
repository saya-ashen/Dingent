from typing import Literal, TypedDict, TypeVar

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    model_validator,
)
from pydantic_settings import BaseSettings

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)


class TablePayload(BaseModel):
    columns: list[str]
    rows: list[dict]
    title: str = ""


class ToolOutput(BaseModel):
    type: str

    payload: TablePayload

    metadata: dict = {}


class BasePluginUserConfig(TypedDict):
    """
    用户可配置项的基类。
    插件开发者应继承此类来定义自己的配置模型。
    """

    name: str
    type_name: str


class ExecutionModel(BaseModel):
    """定义插件的运行方式"""

    mode: Literal["local", "remote"] = Field(..., description="运行模式: 'local' 或 'remote'")

    url: str | None = None
    script_path: FilePath | None = Field(None, description="插件管理器需要运行的Python入口文件路径")
    mcp_json_path: FilePath | None = None

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
    dependencies: list[str] = Field([], description="插件运行所需的Python依赖库列表")
