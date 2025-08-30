from typing import Any

from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel

from dingent.core.log_manager import LogManager


class LLMManager:
    """
    A class to manage and maintain instances of large language models (LLMs).
    This class responsibles for creating and caching LLM instances based on configuration,
    ensuring efficient resource utilization, and providing a unified access point for the application.
    """

    def __init__(self, log_manager: LogManager):
        self._llms: dict[Any, BaseChatModel] = {}
        self._log_manager = log_manager

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
            self._log_manager.log_with_context("info", "Returning cached LLM instance.", context={"params": kwargs_hidden})
            return self._llms[cache_key]

        if "model_provider" not in kwargs and "provider" in kwargs:
            kwargs["model_provider"] = kwargs.pop("provider")

        model_instance = init_chat_model(**kwargs)
        self._llms[cache_key] = model_instance
        self._log_manager.log_with_context("info", "LLM instance created and cached.", context={"params": kwargs_hidden})

        return model_instance

    def list_available_llms(self) -> list[str]:
        return list(self._llms.keys())
