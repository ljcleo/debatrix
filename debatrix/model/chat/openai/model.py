from asyncio import Semaphore
from logging import WARNING, Logger, getLogger

from httpx import AsyncClient
from openai import AsyncOpenAI, BadRequestError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from ....util import sanitize
from ...common import ChatHistory, ChatMessage, ChatRole
from ..base import ChatModelABC
from .config import OpenAIChatModelConfig


class OpenAIChatModel(ChatModelABC):
    def __init__(self) -> None:
        self._semaphore = Semaphore(value=8)
        self._logger: Logger = getLogger(__name__)

        self._client_info_updated: bool = False
        self._opening_client: AsyncOpenAI | None = None

    @property
    def config(self) -> OpenAIChatModelConfig:
        return self._config

    @config.setter
    def config(self, config: OpenAIChatModelConfig) -> None:
        self._config = config
        self._client_info_updated = True

    async def close(self) -> None:
        if self._opening_client is not None:
            await self._opening_client.close()

    async def predict(self, *, messages: ChatHistory) -> ChatMessage:
        client: AsyncOpenAI = await self._get_client()

        async with self._semaphore:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(10),
                wait=wait_random_exponential(min=4, max=60),
                retry=retry_if_not_exception_type((RuntimeError, BadRequestError)),
                before_sleep=before_sleep_log(self._logger, log_level=WARNING, exc_info=True),
            ):
                with attempt:
                    completion: ChatCompletion = await client.chat.completions.create(
                        messages=self._prepare_messages(messages),
                        model=self.config.model,
                        seed=19260817,
                        temperature=0.0,
                    )

                    stop_reason: str = completion.choices[0].finish_reason
                    if stop_reason != "stop":
                        raise RuntimeError(f"response doesn't stop properly: {stop_reason}")

                    return ChatMessage(
                        role=ChatRole.AI,
                        content=sanitize(completion.choices[0].message.content, ""),
                    )

        raise RuntimeError("predict direct result not received")

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

    @staticmethod
    def _prepare_messages(messages: ChatHistory, /) -> list[ChatCompletionMessageParam]:
        prepared: list[ChatCompletionMessageParam] = []

        for message in messages:
            if message.role is ChatRole.SYSTEM:
                prepared.append({"role": "system", "content": message.content})
            elif message.role is ChatRole.AI:
                prepared.append({"role": "assistant", "content": message.content})
            else:
                prepared.append({"role": "user", "content": message.content})

        return prepared
