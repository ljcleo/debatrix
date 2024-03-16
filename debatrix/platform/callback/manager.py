from asyncio import Event, TaskGroup
from collections.abc import Coroutine
from typing import Any, Generic, TypeVar

from .arranger import CallbackArranger
from .common import CallbackStage

T = TypeVar("T")


class CallbackArrangerManager(Generic[T]):
    def __init__(self) -> None:
        self._arrangers: dict[str, dict[T, CallbackArranger]] = {}

    async def serve(self) -> None:
        try:
            async with TaskGroup() as self._tg:
                self._tg.create_task(Event().wait())
        finally:
            for session_id in self._arrangers:
                self.reset(session_id)

    def create(self, session_id: str, /) -> None:
        self._arrangers[session_id] = {}

    def reset(self, session_id: str, /) -> None:
        for arranger in self._arrangers[session_id].values():
            arranger.halt()

        self._arrangers[session_id].clear()

    def put(
        self,
        session_id: str,
        coroutine: Coroutine[Any, Any, None],
        /,
        *,
        stage: CallbackStage,
        key: T,
        proceed: bool = True,
    ) -> None:
        if key not in self._arrangers[session_id]:
            self._arrangers[session_id][key] = CallbackArranger(self._tg)

        self._arrangers[session_id][key].put(coroutine, stage=stage, proceed=proceed)
