from langchain.chat_models.base import BaseChatModel
from langchain_core.vectorstores import VectorStore

from dingent.engine.plugins import BaseTool

from .settings import Settings


class FakeTool(BaseTool):
    def __init__(
        self,
        config: Settings,
        llm: BaseChatModel,
        vectorstore: VectorStore,
        **kwargs,
    ):
        super().__init__(**kwargs)
        print("init success!")

    async def tool_run(self, *args, **kwargs) -> dict:
        return await super().tool_run(*args, **kwargs)
