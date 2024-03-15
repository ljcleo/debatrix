from asyncio import sleep
from collections import deque
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask

from .common import APIResponse
from .session import SessionCache
from .util import prettify_exception

P = ParamSpec("P")


class APIServer:
    def __init__(self, *, debug: bool = False) -> None:
        self._app = FastAPI(debug=debug)
        self._cache_queue: deque[int] = deque()
        self._cache_result: dict[int, APIResponse] = {}

    @property
    def app(self) -> FastAPI:
        return self._app

    def assign(self, path: str, func: Callable[P, Coroutine[Any, Any, Any]]) -> None:
        cache = SessionCache(func=func)

        @wraps(
            func,
            assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            updated=("__annotations__", "__dict__"),
        )
        def assign(*args: P.args, **kwargs: P.kwargs) -> APIResponse[str]:
            key: str = cache.assign(*args, **kwargs)

            try:
                return APIResponse(finished=True, cancelled=False, error=None, result=key)
            except Exception as e:
                return APIResponse(
                    finished=True, cancelled=False, error=prettify_exception(e), result=None
                )

        def start(key: str) -> JSONResponse:
            try:
                if cache[key].is_started:
                    return JSONResponse(
                        APIResponse(
                            finished=True, cancelled=False, error=None, result=True
                        ).to_dict()
                    )

                cache[key].is_started = True

                return JSONResponse(
                    APIResponse(finished=True, cancelled=False, error=None, result=False).to_dict(),
                    background=BackgroundTask(cache[key].bg_func),
                )
            except Exception as e:
                return JSONResponse(
                    APIResponse(
                        finished=True, cancelled=False, error=prettify_exception(e), result=None
                    ).to_dict()
                )

        async def status(key: str) -> APIResponse:
            try:
                for _ in range(1000):
                    await sleep(0.01)
                    if cache[key].response.finished:
                        break

                return cache[key].response
            except Exception as e:
                return APIResponse(
                    finished=True, cancelled=False, error=prettify_exception(e), result=None
                )

        async def cancel(key: str) -> APIResponse:
            try:
                return APIResponse(
                    finished=True, cancelled=False, error=None, result=await cache.cancel(key)
                )
            except Exception as e:
                return APIResponse(
                    finished=True, cancelled=False, error=prettify_exception(e), result=None
                )

        assign.__annotations__["return"] = APIResponse
        self._app.post(path, response_model=APIResponse[str])(assign)
        self._app.put(f"{path}/start", response_model=APIResponse[bool])(start)
        self._app.get(f"{path}/status", response_model=APIResponse)(status)
        self._app.put(f"{path}/cancel", response_model=APIResponse)(cancel)
