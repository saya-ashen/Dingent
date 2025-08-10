from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dingent.engine.plugins.types import BasePluginUserConfig


class AssistantSettings(BaseSettings):
    """ """

    model_config = SettingsConfigDict(env_prefix="DING_")

    name: str = Field(..., description="")
    description: str
    tools: list[BasePluginUserConfig] = []
    version: str | float = Field("0.2.0", description="")
    spec_version: str | float = Field("2.0", description="")
