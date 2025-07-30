from typing import Any

from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel


class LLMManager:
    """
    管理和维护所有大语言模型（LLM）实例的类。

    这个类负责根据配置文件按需创建和缓存LLM实例，
    确保资源被有效利用，并为应用程序提供一个统一的访问点。
    """

    def __init__(self):
        # 用于缓存已实例化的LLM对象，避免重复创建
        self._llms: dict[Any, BaseChatModel] = {}

    def get_llm(self, **kwargs) -> BaseChatModel:
        """
        获取一个指定名称的LLM实例。

        如果实例已存在于缓存中，则直接返回。
        否则，根据配置创建新实例，存入缓存，然后返回。

        """
        cache_key = tuple(sorted(kwargs.items()))
        if cache_key in self._llms:
            print(f"Returning cached LLM instance with params: {kwargs}")
            return self._llms[cache_key]

        if "model_provider" not in kwargs and "provider" in kwargs:
            kwargs["model_provider"] = kwargs.pop("provider")

        model_instance = init_chat_model(**kwargs)

        # 存入缓存
        self._llms[cache_key] = model_instance
        print(f"LLM instance with params '{kwargs}' created and cached.")

        return model_instance

    def list_available_llms(self) -> list[str]:
        """返回所有已配置的LLM的参数列表。"""
        return list(self._llms.keys())
