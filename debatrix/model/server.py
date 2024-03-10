from asyncio import TaskGroup

from ..api import APIServer
from .chat import ChatModel
from .config import ModelConfig
from .embed import EmbedModel


class ModelServer(APIServer):
    def __init__(self, *, debug: bool = False) -> None:
        super().__init__(debug=debug)

        self._chat_model = ChatModel()
        self._embed_model = EmbedModel()

        self.assign_iter("/predict", self._chat_model.predict)
        self.assign("/predict_direct", self._chat_model.predict_direct)
        self.assign("/embed_one", self._embed_model.embed_one)
        self.assign("/embed_many", self._embed_model.embed_many)

    @property
    def config(self) -> ModelConfig:
        return self._config

    @config.setter
    def config(self, config: ModelConfig) -> None:
        self._config = config
        self._chat_model.config = config.chat_config
        self._embed_model.config = config.embed_config

    async def close(self) -> None:
        async with TaskGroup() as tg:
            for model in (self._chat_model, self._embed_model):
                tg.create_task(model.close())
