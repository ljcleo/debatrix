from asyncio import Event, Queue, Task, TaskGroup
from collections.abc import Coroutine
from typing import Any

from .common import CallbackStage


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
        try:
            async with TaskGroup() as tg:
                poll_task: Task[None] = tg.create_task(self._poll())
                await self._halt.wait()
                poll_task.cancel()
        finally:
            for queue in self._queues.values():
                while not queue.empty():
                    queue.get_nowait()[0].close()

    async def _poll(self) -> None:
        stage: CallbackStage = CallbackStage.PRE

        while True:
            coroutine: Coroutine[Any, Any, None]
            proceed: bool
            coroutine, proceed = await self._queues[stage].get()
            await coroutine

            if proceed:
                stage = CallbackStage(stage % len(CallbackStage) + 1)
