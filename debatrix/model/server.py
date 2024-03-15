from asyncio import TaskGroup
from typing import Annotated

from fastapi import Body

from ..api import APIServer
from .chat import ChatModel
from .common import ChatHistory, ChatMessage
from .config import ModelConfig
from .embed import EmbedModel


class ModelServer(APIServer):
    def __init__(self, *, debug: bool = False) -> None:
        super().__init__(debug=debug)

        self._models: dict[str, tuple[ChatModel, EmbedModel]] = {}

        self.assign("/{session_id}/create", self._create)
        self.assign("/{session_id}/configure", self._configure)

        self.assign("/{session_id}/chat/predict", self._chat_predict)

        self.assign("/{session_id}/embed/one", self._embed_one)
        self.assign("/{session_id}/embed/many", self._embed_many)

    async def close(self) -> None:
        async with TaskGroup() as tg:
            for chat_model, embed_model in self._models.values():
                tg.create_task(chat_model.close())
                tg.create_task(embed_model.close())

    async def _create(self, session_id: str) -> None:
        self._models[session_id] = (ChatModel(), EmbedModel())

    async def _configure(self, session_id: str, config: ModelConfig) -> None:
        self._models[session_id][0].config = config.chat_config
        self._models[session_id][1].config = config.embed_config

    async def _chat_predict(self, session_id: str, messages: ChatHistory) -> ChatMessage:
        return await self._models[session_id][0].predict(messages=messages)

    async def _embed_one(self, session_id: str, text: Annotated[str, Body()]) -> list[float]:
        return await self._models[session_id][1].embed_one(text=text)

    async def _embed_many(self, session_id: str, batch: list[str]) -> list[list[float]]:
        return await self._models[session_id][1].embed_many(batch=batch)
