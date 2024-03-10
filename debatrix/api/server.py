from asyncio import CancelledError, Task, sleep
from collections import deque
from collections.abc import AsyncIterator, Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from starlette.background import BackgroundTask

from .common import APIResponse
from .session import SessionCache
from .util import prettify_exception, pydantic_dump_json

P = ParamSpec("P")


class APIServer:
    def __init__(self, *, debug: bool = False) -> None:
        self._app = FastAPI(debug=debug)
        self._cache_queue: deque[int] = deque()
        self._cache_result: dict[int, APIResponse] = {}
        self._running_tasks: set[Task[Any]] = set()

    @property
    def app(self) -> FastAPI:
        return self._app

    def assign(self, path: str, func: Callable[P, Coroutine[Any, Any, Any]]) -> None:
        cache = SessionCache(func=func, task_pool=self._running_tasks)

        @wraps(
            func,
            assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            updated=("__annotations__", "__dict__"),
        )
        def assign(*args: P.args, **kwargs: P.kwargs) -> APIResponse[str]:
            key: str = cache.assign(*args, **kwargs)

            try:
                return APIResponse(finished=True, error=None, result=key)
            except Exception as e:
                return APIResponse(finished=True, error=prettify_exception(e), result=None)

        def start(key: str) -> JSONResponse:
            try:
                if cache[key].is_started:
                    return JSONResponse(
                        APIResponse(finished=True, error=None, result=True).to_dict()
                    )

                cache[key].is_started = True

                return JSONResponse(
                    APIResponse(finished=True, error=None, result=False).to_dict(),
                    background=BackgroundTask(cache[key].bg_func),
                )
            except Exception as e:
                return JSONResponse(
                    APIResponse(finished=True, error=prettify_exception(e), result=None).to_dict()
                )

        async def status(key: str) -> APIResponse:
            try:
                for _ in range(1000):
                    await sleep(0.01)
                    if cache[key].response.finished:
                        break

                return cache[key].response
            except Exception as e:
                return APIResponse(finished=True, error=prettify_exception(e), result=None)

        assign.__annotations__["return"] = APIResponse
        self._app.post(path, response_model=APIResponse[str])(assign)
        self._app.put(f"{path}/start", response_model=APIResponse[bool])(start)
        self._app.get(f"{path}/status", response_model=APIResponse)(status)

    def assign_iter(self, path: str, func: Callable[P, AsyncIterator], /) -> None:
        @wraps(
            func,
            assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            updated=("__annotations__", "__dict__"),
        )
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> EventSourceResponse:
            async def inner_wrapped():
                def wrap(data: str, /) -> bytes:
                    return ServerSentEvent(data=data).encode()

                try:
                    async for chunk in func(*args, **kwargs):
                        yield wrap(
                            pydantic_dump_json(
                                APIResponse(finished=False, error=None, result=chunk)
                            )
                        )
                except Exception as e:
                    yield wrap(
                        pydantic_dump_json(
                            APIResponse(finished=False, error=prettify_exception(e), result=None)
                        )
                    )

                yield wrap(pydantic_dump_json(APIResponse(finished=True, error=None, result=None)))

            return EventSourceResponse(inner_wrapped())

        wrapped.__annotations__["return"] = EventSourceResponse
        self._app.post(path, response_model=None, response_class=EventSourceResponse)(wrapped)

    async def cancel_tasks(self) -> None:
        for task in list(self._running_tasks):
            task.cancel()

            try:
                await task
            except CancelledError:
                pass

            self._running_tasks.discard(task)
