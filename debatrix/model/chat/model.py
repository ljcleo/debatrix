from collections.abc import AsyncIterator

from ..common import ChatHistory, ChatMessage
from .base import ChatModelABC
from .config import ChatModelBackend, ChatModelConfig
from .openai import OpenAIChatModel
from .test import TestChatModel


class ChatModel(ChatModelABC):
    def __init__(self) -> None:
        self._test_model = TestChatModel()
        self._openai_model = OpenAIChatModel()

    @property
    def config(self) -> ChatModelConfig:
        return self._config

    @config.setter
    def config(self, config: ChatModelConfig) -> None:
        self._config = config
        self._test_model.config = config.test_config
        self._openai_model.config = config.openai_config

    async def close(self) -> None:
        await self._openai_model.close()

    async def predict(self, messages: ChatHistory) -> AsyncIterator[ChatMessage]:
        async for chunk in self._get_model().predict(messages):
            yield chunk

    async def predict_direct(self, messages: ChatHistory) -> ChatMessage:
        return await self._get_model().predict_direct(messages)

    def _get_model(self, backend: ChatModelBackend | None = None, /) -> ChatModelABC:
        if backend is None:
            backend = self.config.backend

        if backend == ChatModelBackend.TEST:
            return self._test_model
        elif backend == ChatModelBackend.OPENAI:
            return self._openai_model
        else:
            raise ValueError(backend)
