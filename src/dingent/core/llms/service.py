import os
from functools import lru_cache

from langchain_litellm import ChatLiteLLM


@lru_cache(maxsize=20)
def get_llm(**kwargs) -> ChatLiteLLM:
    return ChatLiteLLM(**kwargs)
