from pathlib import Path
from typing import Any

import tomlkit
from loguru import logger
from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from dingent.engine.plugins.types import PluginUserConfig
from dingent.utils import find_project_root


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


# --- 2. Refactored Pydantic Models ---


class AssistantSettings(BaseSettings):
    name: str = Field(..., description="The name of the assistant.")
    description: str
    plugins: list[PluginUserConfig] = []
    version: str | float = Field("0.2.0", description="Assistant version.")
    spec_version: str | float = Field("2.0", description="Specification version.")
    enabled: bool = Field(True, description="Enable or disable the assistant.")


class AppSettings(BaseSettings):
    # All configuration is now centralized here.
    # The prefix applies to environment variables for AppSettings fields.
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    assistants: list[AssistantSettings] = []
    default_assistant: str | None = None
    llm: dict[str, str | int] = {}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Define the priority of configuration sources.
        Order is: Toml file -> .env file -> Environment variables.
        """
        return (
            dotenv_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),  # Our custom TOML loader
            init_settings,  # Values passed on initialization
            file_secret_settings,
        )

    def save(self):
        """
        Saves the current configuration back to the config.toml file,
        preserving comments and formatting.
        """
        source = TomlConfigSettingsSource(self.__class__)
        if not source.toml_path:
            logger.error("Cannot save settings: Project root or config path not found.")
            return

        # config_data = self.model_dump(mode="json", exclude_none=True)
        doc = tomlkit.parse(source.toml_path.read_text())

        source.toml_path.write_text(tomlkit.dumps(doc), "utf-8")
        logger.success(f"Configuration saved successfully to {source.toml_path}")
