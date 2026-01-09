import os
from functools import lru_cache

from langchain_litellm import ChatLiteLLM


@lru_cache(maxsize=20)
def get_llm_service(**kwargs) -> ChatLiteLLM:
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL", "gpt-4.1")
    return ChatLiteLLM(**kwargs, api_base=api_base, model=model)
