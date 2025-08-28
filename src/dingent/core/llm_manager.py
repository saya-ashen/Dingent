from typing import Any

from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel


class LLMManager:
    """
    A class to manage and maintain instances of large language models (LLMs).
    This class responsibles for creating and caching LLM instances based on configuration,
    ensuring efficient resource utilization, and providing a unified access point for the application.
    """

    def __init__(self):
        self._llms: dict[Any, BaseChatModel] = {}

    def get_llm(self, **kwargs):
        """
        Get a LLM instance by its name.
        If the instance already exists in the cache, return it directly.
        Otherwise, create a new instance based on the provided configuration,

        """
        cache_key = tuple(sorted(kwargs.items()))
        kwargs_hidden = {k: ("***" if k == "api_key" else v) for k, v in kwargs.items()}
        if cache_key in self._llms:
            print(f"Returning cached LLM instance with params: {kwargs_hidden}")
            return self._llms[cache_key]

        if "model_provider" not in kwargs and "provider" in kwargs:
            kwargs["model_provider"] = kwargs.pop("provider")

        model_instance = init_chat_model(**kwargs)
        self._llms[cache_key] = model_instance
        print(f"LLM instance with params '{kwargs_hidden}' created and cached.")

        return model_instance

    def list_available_llms(self) -> list[str]:
        return list(self._llms.keys())
