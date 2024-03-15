from asyncio import CancelledError
from logging import Logger, getLogger, WARNING
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, Literal, TypeVar

from aiohttp import ClientResponse, ClientSession, ClientTimeout
from tenacity import (
    AsyncRetrying,
    retry_unless_exception_type,
    stop_after_attempt,
    wait_random,
    wait_random_exponential,
    before_sleep_log,
)

from ..util import sanitize
from .common import APIResponse, ServerInfo
from .util import pydantic_dump_json, pydantic_load_json

T = TypeVar("T")


class APIClient:
    def __init__(self, *, timeout: int = 30) -> None:
        self._info_updated: bool = False
        self._opened_session: ClientSession | None = None
        self._timeout = ClientTimeout(total=timeout)
        self._logger: Logger = getLogger(__name__)

    @property
    def address(self) -> str:
        return self._server_info.address

    @property
    def sub_path(self) -> str:
        return sanitize(self._server_info.sub_path, "")

    def set_server_info(self, info: ServerInfo, /) -> None:
        if self._opened_session is None or info != self._server_info:
            self._server_info = info
            self._info_updated = True

    async def close(self) -> None:
        if self._opened_session is not None:
            await self._opened_session.close()
            self._opened_session = None

    async def query(
        self,
        path: str,
        data: Any | None = None,
        /,
        *,
        output_type: type[T],
        extra_headers: Mapping[str, str] | None = None,
        max_retries: int = 3,
    ) -> T | None:
        key: str | None = None

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_retries),
                wait=wait_random_exponential(multiplier=4, max=60),
                before_sleep=before_sleep_log(self._logger, log_level=WARNING, exc_info=True),
            ):
                with attempt:
                    async with self._request(path, data, extra_headers=extra_headers) as response:
                        text: str = await response.text(encoding="utf8")
                        if response.status != 200:
                            raise RuntimeError(response.status, text)

                    key: str | None = self._parse(text, str)[1]
                    assert key is not None

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_retries),
                wait=wait_random_exponential(multiplier=4, max=60),
                before_sleep=before_sleep_log(self._logger, log_level=WARNING, exc_info=True),
            ):
                with attempt:
                    async with self._request(f"{path}/start?key={key}", mode="put") as response:
                        text: str = await response.text(encoding="utf8")
                        if response.status != 200:
                            raise RuntimeError(response.status, text)

                    self._parse(text, bool)

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_retries),
                wait=wait_random_exponential(multiplier=4, max=60),
                before_sleep=before_sleep_log(self._logger, log_level=WARNING, exc_info=True),
            ):
                with attempt:
                    async for inner_attempt in AsyncRetrying(
                        wait=wait_random(min=3, max=5), retry=retry_unless_exception_type()
                    ):
                        with inner_attempt:
                            async with self._request(
                                f"{path}/status?key={key}", mode="get"
                            ) as response:
                                text: str = await response.text(encoding="utf8")
                                if response.status != 200:
                                    raise RuntimeError(response.status, text)

                            finished: bool
                            result: T | None
                            finished, result = self._parse(text, output_type)

                            if finished:
                                return result
        except CancelledError:
            print("Sending cancel signal to", path, "...")

            try:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(max_retries),
                    wait=wait_random_exponential(multiplier=4, max=60),
                    before_sleep=before_sleep_log(self._logger, log_level=WARNING, exc_info=True),
                ):
                    with attempt:
                        async with self._request(
                            f"{path}/cancel?key={key}", mode="put"
                        ) as response:
                            text: str = await response.text(encoding="utf8")
                            if response.status != 200:
                                raise RuntimeError(response.status, text)

                        self._parse(text, bool)
            except CancelledError:
                pass

    @asynccontextmanager
    async def _request(
        self,
        path: str,
        data: Any | None = None,
        /,
        *,
        mode: Literal["post", "put", "get"] = "post",
        extra_headers: Mapping[str, str] | None = None,
    ) -> AsyncIterator[ClientResponse]:
        if self._info_updated:
            await self.close()
            self._session = ClientSession(self.address, timeout=self._timeout)
            self._opened_session = self._session
            self._info_updated = False

        headers: dict[str, str] = {"content-type": "application/json"}
        if extra_headers is not None:
            headers.update(extra_headers)

        if data is not None:
            if mode == "get":
                raise RuntimeError("get method cannot send data")

            data = pydantic_dump_json(data).encode()

        if mode == "post":
            async with self._session.post(
                f"{self.sub_path}{path}", data=data, headers=headers
            ) as response:
                yield response
        elif mode == "put":
            async with self._session.put(
                f"{self.sub_path}{path}", data=data, headers=headers
            ) as response:
                yield response
        elif mode == "get":
            async with self._session.get(f"{self.sub_path}{path}", headers=headers) as response:
                yield response
        else:
            raise RuntimeError(mode)

    def _parse(self, text: str, target: type[T], /) -> tuple[bool, T | None]:
        result: APIResponse[target] = pydantic_load_json(text, APIResponse[target])
        if result.error is not None:
            raise RuntimeError(result.error)

        return result.finished, result.result
