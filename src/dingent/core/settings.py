import uuid
from pathlib import Path
from typing import Any

import tomlkit
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
)

from .types import AssistantBase, PluginUserConfig
from .utils import find_project_root


# --- 1. Custom Source for TOML file loading ---
# This class tells pydantic-settings HOW to load our config.toml file.
class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source class that loads variables from a TOML file.
    """

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        self.project_root: Path | None = find_project_root()
        if self.project_root:
            self.toml_path = self.project_root / "backend" / "config.toml"
        else:
            self.toml_path = None

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        if not self.toml_path or not self.toml_path.is_file():
            return None, "", False

        file_content = tomlkit.parse(self.toml_path.read_text("utf-8"))
        field_value = file_content.get(field_name)
        return field_value, field_name, True

    def __call__(self) -> dict[str, Any]:
        if not self.toml_path or not self.toml_path.is_file():
            logger.warning("config.toml not found. Skipping.")
            return {}

        logger.info(f"Loading settings from: {self.toml_path}")
        return tomlkit.loads(self.toml_path.read_text()).unwrap()


class AssistantSettings(AssistantBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the assistant, automatically generated if not provided.")
    plugins: list[PluginUserConfig] = []


class LlmSettings(BaseModel):
    model: str = Field(..., description="The name of the LLM model to use.")
    provider: str | None = Field(None, description="The provider of the LLM model (e.g., 'openai', 'anthropic').")
    base_url: str | None = Field(None, description="Base URL for the LLM provider, if applicable.")
    api_key: str | None = Field(None, description="API key for the LLM provider, if applicable.")


class AppSettings(BaseModel):
    model_config = ConfigDict(env_prefix="DINGENT_", populate_by_name=True, extra="ignore")
    assistants: list[AssistantSettings] = []
    default_assistant: str | None = None
    llm: LlmSettings

    def save(self):
        """
        Saves the current configuration back to the config.toml file,
        preserving comments and formatting.
        """
        source = TomlConfigSettingsSource(self.__class__)
        if not source.toml_path:
            logger.error("Cannot save settings: Project root or config path not found.")
            return

        config_data = self.model_dump(mode="json", exclude_none=True)
        doc = tomlkit.parse(source.toml_path.read_text())
        doc.update(config_data)

        source.toml_path.write_text(tomlkit.dumps(doc, sort_keys=True), "utf-8")
        logger.success(f"Configuration saved successfully to {source.toml_path}")
