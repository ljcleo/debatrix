from asyncio import Lock, Task, TaskGroup
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from ....common import ANone
from ....core.action import AllPanelActions
from ....core.common import DimensionName

T = TypeVar("T")
StreamingCallback = Callable[[AllPanelActions, DimensionName, tuple[str, str] | None], ANone]


class BiModeTaskGroup(TaskGroup):
    def __init__(self, *, concurrent: bool = True) -> None:
        super().__init__()
        self._lock: Lock | None = None if concurrent else Lock()

    def create_task(self, coroutine: Coroutine[Any, Any, T]) -> Task[T]:
        async def wrapped() -> T:
            if self._lock is not None:
                async with self._lock:
                    return await coroutine
            else:
                return await coroutine

        return super().create_task(wrapped())
