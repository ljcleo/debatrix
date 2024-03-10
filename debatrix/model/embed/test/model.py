from random import Random

from ..base import EmbedModelABC


class TestEmbedModel(EmbedModelABC):
    async def embed_one(self, text: str) -> list[float]:
        gen = Random(x=hash(text))
        return [gen.random() - 0.5 for _ in range(1536)]

    async def embed_many(self, batch: list[str]) -> list[list[float]]:
        return [await self.embed_one(text) for text in batch]
