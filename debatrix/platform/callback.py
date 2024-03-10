import enum
from asyncio import Event, Queue, Task, TaskGroup
from collections.abc import Coroutine
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@enum.unique
class CallbackStage(enum.IntEnum):
    PRE = enum.auto()
    IN = enum.auto()
    POST = enum.auto()


class CallbackArranger:
    def __init__(self, tg: TaskGroup, /) -> None:
        self._queues: dict[CallbackStage, Queue[tuple[Coroutine[Any, Any, None], bool]]] = {
            key: Queue() for key in CallbackStage
        }

        self._halt = Event()
        tg.create_task(self._serve())

    def put(
        self, coroutine: Coroutine[Any, Any, None], /, *, stage: CallbackStage, proceed: bool = True
    ) -> None:
        self._queues[stage].put_nowait((coroutine, proceed))

    def halt(self) -> None:
        self._halt.set()

    async def _serve(self) -> None:
        async with TaskGroup() as tg:
            poll_task: Task[None] = tg.create_task(self._poll())
            await self._halt.wait()
            poll_task.cancel()

        for queue in self._queues.values():
            while not queue.empty():
                queue.get_nowait()[0].close()

    async def _poll(self) -> None:
        stage = CallbackStage.PRE

        while True:
            coroutine: Coroutine[Any, Any, None]
            proceed: bool
            coroutine, proceed = await self._queues[stage].get()
            await coroutine

            if proceed:
                stage = CallbackStage(stage % len(CallbackStage) + 1)


class CallbackArrangerManager(Generic[T]):
    def __init__(self) -> None:
        self._arrangers: dict[T, CallbackArranger] = {}

    def reset(self) -> None:
        for arranger in self._arrangers.values():
            arranger.halt()

        self._arrangers.clear()

    def put(
        self,
        coroutine: Coroutine[Any, Any, None],
        /,
        *,
        stage: CallbackStage,
        key: T,
        proceed: bool = True,
    ) -> None:
        if key not in self._arrangers:
            self._arrangers[key] = CallbackArranger(self._tg)

        self._arrangers[key].put(coroutine, stage=stage, proceed=proceed)

    async def serve(self) -> None:
        async with TaskGroup() as self._tg:
            self._tg.create_task(Event().wait())
