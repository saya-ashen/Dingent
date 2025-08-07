import os

from pydantic import BaseModel, model_validator

from dingent.engine.plugins import ToolBaseSettings


class DatabaseSettings(BaseModel):
    name: str
    uri: str = ""
    uri_env: str = ""
    schemas_file: str | None = None
    type: str | None = None

    # TODO: More simple method
    @model_validator(mode="after")
    def determine_type_from_uri(self) -> "DatabaseSettings":
        """
        Runs after all fields are populated to ensure `uri` is available.
        """
        db_uri = self.uri
        if not db_uri:
            if self.uri_env and self.uri_env in os.environ:
                db_uri = os.environ[self.uri_env]
                self.uri = db_uri

        if not db_uri:
            raise ValueError("A database URI must be provided either via 'uri' field or 'uri_env' environment variable.")

        if db_uri.startswith("postgresql"):
            self.type = "postgresql"
        elif db_uri.startswith("mysql"):
            self.type = "mysql"
        elif db_uri.startswith("sqlite"):
            self.type = "sqlite"
        else:
            raise ValueError(f"Could not determine database type from URI: '{db_uri[:30]}...'")

        return self


class Settings(ToolBaseSettings):
    database: DatabaseSettings
    llm: dict[str, str]
