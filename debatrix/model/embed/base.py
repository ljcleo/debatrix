from abc import ABC, abstractmethod


class EmbedModelABC(ABC):
    @abstractmethod
    async def embed_one(self, *, text: str) -> list[float]:
        raise NotImplementedError()

    @abstractmethod
    async def embed_many(self, *, batch: list[str]) -> list[list[float]]:
        raise NotImplementedError()
