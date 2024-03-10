from collections.abc import AsyncIterator, Iterable

from ..api import APIClient
from .common import ChatHistory, ChatMessage


class ModelClient(APIClient):
    async def predict(self, messages: ChatHistory, /) -> AsyncIterator[ChatMessage]:
        async for chunk in self.query_sse("/predict", messages, output_type=ChatMessage):
            if chunk is None:
                raise RuntimeError("predict result is null")

            yield chunk

    async def predict_direct(self, messages: ChatHistory, /) -> ChatMessage:
        result: ChatMessage | None = await self.query(
            "/predict_direct", messages, output_type=ChatMessage
        )
        if result is None:
            raise RuntimeError("predict result is null")

        return result

    async def embed_one(self, text: str, /) -> list[float]:
        result: list[float] | None = await self.query("/embed_one", text, output_type=list[float])
        if result is None:
            raise RuntimeError("embed result is null")

        return result

    async def embed_many(self, batch: Iterable[str], /) -> list[list[float]]:
        result: list[list[float]] | None = await self.query(
            "/embed_many", list(batch), output_type=list[list[float]]
        )

        if result is None:
            raise RuntimeError("embed result is null")

        return result
