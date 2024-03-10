import logging
from asyncio import Semaphore

from httpx import AsyncClient
from openai import AsyncOpenAI, BadRequestError
from openai.types.create_embedding_response import CreateEmbeddingResponse
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    retry_if_not_exception_type,
    wait_random_exponential,
    before_sleep_log,
)

from ..base import EmbedModelABC
from .config import OpenAIEmbedModelConfig


class OpenAIEmbedModel(EmbedModelABC):
    def __init__(self) -> None:
        self._semaphore = Semaphore(value=256)
        self._logger = logging.getLogger(__name__)

        self._client_info_updated: bool = False
        self._opening_client: AsyncOpenAI | None = None

    @property
    def config(self) -> OpenAIEmbedModelConfig:
        return self._config

    @config.setter
    def config(self, config: OpenAIEmbedModelConfig) -> None:
        self._config = config
        self._client_info_updated = True

    async def close(self) -> None:
        if self._opening_client is not None:
            await self._opening_client.close()

    async def embed_one(self, text: str) -> list[float]:
        client: AsyncOpenAI = await self._get_client()

        async with self._semaphore:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(10),
                wait=wait_random_exponential(min=4, max=60),
                retry=retry_if_not_exception_type((RuntimeError, BadRequestError)),
                before_sleep=before_sleep_log(self._logger, log_level=logging.INFO, exc_info=True),
            ):
                with attempt:
                    response: CreateEmbeddingResponse = await client.embeddings.create(
                        input=text, model=self.config.model
                    )

                    return response.data[0].embedding

        raise RuntimeError("embed one result not received")

    async def embed_many(self, batch: list[str]) -> list[list[float]]:
        if len(batch) == 0:
            return []

        client: AsyncOpenAI = await self._get_client()

        async with self._semaphore:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(10),
                wait=wait_random_exponential(min=4, max=60),
                retry=retry_if_not_exception_type((RuntimeError, BadRequestError)),
                before_sleep=before_sleep_log(self._logger, log_level=logging.INFO, exc_info=True),
            ):
                with attempt:
                    response: CreateEmbeddingResponse = await client.embeddings.create(
                        input=batch, model=self.config.model
                    )

                    return [item.embedding for item in response.data]

        raise RuntimeError("embed many result not received")

    async def _get_client(self) -> AsyncOpenAI:
        if self._client_info_updated:
            await self.close()

            proxy: str | None = self.config.proxy
            if proxy == "":
                proxy = None

            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                http_client=AsyncClient(proxies=proxy),
            )

            self._client_info_updated = False
            self._opening_client = self._client

        return self._client
