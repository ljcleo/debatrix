from asyncio import CancelledError, Task, TaskGroup
from collections.abc import Callable, Coroutine
from queue import Queue
from typing import Any, Generic, ParamSpec, TypeVar
from uuid import uuid4

from pydantic import Field
from pydantic.dataclasses import dataclass

from ..common import ANone
from .common import APIResponse
from .util import prettify_exception

T = TypeVar("T")
P = ParamSpec("P")


@dataclass
class SessionData(Generic[T]):
    bg_func: Callable[[], ANone]
    is_started: bool = False

    response: APIResponse[T] = Field(
        default_factory=lambda: APIResponse(
            finished=False, cancelled=False, error=None, result=None
        )
    )


class SessionCache(Generic[P, T]):
    def __init__(
        self, *, func: Callable[P, Coroutine[Any, Any, T]], max_size: int = 100000
    ) -> None:
        self._func = func
        self._max_size = max_size

        self._cache: dict[str, SessionData[T]] = {}
        self._task_pool: dict[str, Task[Any]] = {}
        self._queue: Queue[str] = Queue()

    def __getitem__(self, key: str, /) -> SessionData[T]:
        return self._cache[key]

    def assign(self, *args: P.args, **kwargs: P.kwargs) -> str:
        key: str = self._generate_key()
        self._queue.put_nowait(key)

        async def bg_func() -> None:
            try:
                try:
                    async with TaskGroup() as tg:
                        task: Task[T] = tg.create_task(self._func(*args, **kwargs))
                        self._task_pool[key] = task

                    self[key].response = APIResponse(
                        finished=True, cancelled=False, error=None, result=task.result()
                    )
                except CancelledError as e:
                    self[key].response = APIResponse(
                        finished=True, cancelled=True, error=prettify_exception(e), result=None
                    )

            except Exception as e:
                print(prettify_exception(e))

                self[key].response = APIResponse(
                    finished=True, cancelled=False, error=prettify_exception(e), result=None
                )

            if key in self._task_pool:
                del self._task_pool[key]

        self._cache[key] = SessionData(bg_func=bg_func)
        return key

    async def cancel(self, key: str, /) -> bool:
        if key in self._task_pool and not self._task_pool[key].done():
            self._task_pool[key].cancel()

            try:
                await self._task_pool[key]
            except CancelledError:
                pass

            return False
        else:
            return True

    def _generate_key(self) -> str:
        while len(self._cache) > self._max_size:
            old_key: str = self._queue.get_nowait()

            if old_key in self._cache:
                del self._cache[old_key]
            if old_key in self._task_pool:
                del self._task_pool[old_key]

        return uuid4().hex
