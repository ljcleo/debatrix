from collections.abc import Iterable
from types import NoneType
from urllib.parse import quote

from ..api import APIClient
from .common import ChatHistory, ChatMessage
from .config import ModelConfig


class ModelClient(APIClient):
    def __init__(self, *, session_id: str, timeout: int = 30) -> None:
        super().__init__(timeout=timeout)
        self._session_id = session_id

    async def create(self) -> None:
        await self.query(self._quote("/create"), output_type=NoneType)

    async def configure(self, *, config: ModelConfig) -> None:
        await self.query(self._quote("/configure"), config, output_type=NoneType)

    async def chat_predict(self, *, messages: ChatHistory) -> ChatMessage:
        result: ChatMessage | None = await self.query(
            self._quote("/chat/predict"), messages, output_type=ChatMessage
        )

        if result is None:
            raise RuntimeError("predict result is null")

        return result

    async def embed_one(self, *, text: str) -> list[float]:
        result: list[float] | None = await self.query(
            self._quote("/embed/one"), text, output_type=list[float]
        )

        if result is None:
            raise RuntimeError("embed result is null")

        return result

    async def embed_many(self, *, batch: Iterable[str]) -> list[list[float]]:
        result: list[list[float]] | None = await self.query(
            self._quote("/embed/many"), list(batch), output_type=list[list[float]]
        )

        if result is None:
            raise RuntimeError("embed result is null")

        return result

    def _quote(self, path: str) -> str:
        return quote(f"/{self._session_id}{path}")
