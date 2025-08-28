import uuid
from pathlib import Path
from typing import Any

import tomlkit
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from .types import AssistantBase, PluginUserConfig, Workflow
from .utils import find_project_root


class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        self.project_root: Path | None = find_project_root()
        if self.project_root:
            self.toml_path = self.project_root / "dingent.toml"
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
            logger.warning("dingent.toml not found. Skipping TomlConfigSettingsSource.")
            return {}
        logger.info(f"Loading global settings from: {self.toml_path}")
        return tomlkit.loads(self.toml_path.read_text()).unwrap()


class AssistantSettings(AssistantBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the assistant.")
    plugins: list[PluginUserConfig] = []


class LLMSettings(BaseModel):
    model: str = Field("gpt-4.1", description="LLM model name.")
    provider: str | None = Field(None, description="Provider name.")
    base_url: str | None = Field(None, description="Base URL.")
    api_key: str | None = Field(None, description="API key.")


class AppSettings(BaseModel):
    model_config = ConfigDict(env_prefix="DINGENT_", populate_by_name=True, extra="ignore")
    assistants: list[AssistantSettings] = []
    llm: LLMSettings = LLMSettings()
    backend_port: int = 8000
    frontend_port: int = 8080
    workflows: list[Workflow] = Field(default_factory=list, description="All workflows cached in settings")
    current_workflow: str | None = Field(None, description="ID of the current workflow")

    def save(self):
        source = TomlConfigSettingsSource(self.__class__)
        if not source.toml_path:
            logger.error("Cannot save: dingent.toml path not found.")
            return
        data = self.model_dump(mode="json", exclude_none=True)
        data = {k: v for k, v in data.items() if k != "assistants"}
        if source.toml_path.is_file():
            doc = tomlkit.parse(source.toml_path.read_text())
        else:
            doc = tomlkit.document()
        doc.update(data)
        source.toml_path.write_text(tomlkit.dumps(doc, sort_keys=True), "utf-8")
        logger.success(f"Global configuration saved to {source.toml_path}")
