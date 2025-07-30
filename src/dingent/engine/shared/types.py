from pydantic import BaseModel


class LLMSettings(BaseModel):
    name: str
    provider: str
    base_url: str = ""
    api_key: str | None = None
