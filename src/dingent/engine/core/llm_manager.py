from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel

from .types import LLMSettings


class LLMManager:
    """
    管理和维护所有大语言模型（LLM）实例的类。

    这个类负责根据配置文件按需创建和缓存LLM实例，
    确保资源被有效利用，并为应用程序提供一个统一的访问点。
    """

    def __init__(self, llm_configs: list[LLMSettings]):
        """
        初始化 LLM 管理器。

        :param llm_configs: 一个配置字典的列表，每个字典描述一个LLM。
                          例如来自于 config.yaml 中的 'llms' 部分。
                          [
                              {'name': 'openai_gpt4', 'provider': 'openai', 'model': 'gpt-4-turbo', ...},
                              {'name': 'local_llama', 'provider': 'ollama', 'model': 'llama3', ...}
                          ]
        """
        # 将配置列表转换为以'name'为键的字典，方便快速查找
        self._configs: dict[str, LLMSettings] = {f"{config.provider}-{config.name}": config for config in llm_configs}
        # 用于缓存已实例化的LLM对象，避免重复创建
        self._llms: dict[str, BaseChatModel] = {}
        print(f"LLMManager initialized with {len(self._configs)} configurations.")

    def get_llm(self, provider: str, name: str) -> BaseChatModel:
        """
        获取一个指定名称的LLM实例。

        如果实例已存在于缓存中，则直接返回。
        否则，根据配置创建新实例，存入缓存，然后返回。

        :param name: 在配置文件中定义的LLM的唯一名称 (例如 'openai_gpt4')。
        :return: 一个 LangChain 的 BaseLanguageModel 实例。
        :raises ValueError: 如果请求的名称在配置中不存在。
        """
        name = f"{provider}-{name}"
        # 1. 检查缓存
        if name in self._llms:
            print(f"Returning cached LLM instance: {name}")
            return self._llms[name]

        # 2. 检查配置是否存在
        if name not in self._configs:
            raise ValueError(f"LLM with name '{name}' not found in configuration.")

        # 3. 按需实例化
        print(f"Creating new LLM instance: {name}...")
        config = self._configs[name]

        # 从配置中提取参数，为你原来的 get_llm 方法提供参数
        # 使用 .get() 方法提供默认值，增加健壮性
        model_name = config.name
        model_provider = config.provider
        base_url = config.base_url
        api_key = config.api_key

        # 准备传递给 init_chat_model 的参数字典
        # 这样可以只传递非 None 的值
        init_params = {
            "model": model_name,
            "model_provider": model_provider,
            "base_url": base_url,
            "api_key": api_key,
        }
        # 过滤掉值为None的参数
        filtered_params = {k: v for k, v in init_params.items() if v is not None}

        model_instance = init_chat_model(**filtered_params)

        # 4. 存入缓存
        self._llms[name] = model_instance
        print(f"LLM instance '{name}' created and cached.")

        return model_instance

    def list_available_llms(self) -> list[str]:
        """返回所有已配置的LLM名称列表。"""
        return list(self._configs.keys())
