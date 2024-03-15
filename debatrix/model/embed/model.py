from .base import EmbedModelABC
from .config import EmbedModelBackend, EmbedModelConfig
from .openai import OpenAIEmbedModel
from .test import TestEmbedModel


class EmbedModel(EmbedModelABC):
    def __init__(self) -> None:
        self._test_model = TestEmbedModel()
        self._openai_model = OpenAIEmbedModel()

    @property
    def config(self) -> EmbedModelConfig:
        return self._config

    @config.setter
    def config(self, config: EmbedModelConfig) -> None:
        self._config = config
        self._openai_model.config = config.openai_config

    async def close(self) -> None:
        await self._openai_model.close()

    async def embed_one(self, *, text: str) -> list[float]:
        return await self._get_model().embed_one(text=text)

    async def embed_many(self, *, batch: list[str]) -> list[list[float]]:
        return await self._get_model().embed_many(batch=batch)

    def _get_model(self, backend: EmbedModelBackend | None = None, /) -> EmbedModelABC:
        if backend is None:
            backend = self.config.backend

        if backend == EmbedModelBackend.TEST:
            return self._test_model
        elif backend == EmbedModelBackend.OPENAI:
            return self._openai_model
        else:
            raise ValueError(backend)
