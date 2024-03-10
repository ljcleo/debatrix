from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ..common import ChatHistory, ChatMessage


class ChatModelABC(ABC):
    @abstractmethod
    async def predict(self, messages: ChatHistory) -> AsyncIterator[ChatMessage]:
        raise NotImplementedError()
        yield

    @abstractmethod
    async def predict_direct(self, messages: ChatHistory) -> ChatMessage:
        raise NotImplementedError()
