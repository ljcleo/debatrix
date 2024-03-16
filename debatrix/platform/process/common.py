import enum
from asyncio import TaskGroup
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing import Queue
from typing import Any

from ...arena import ArenaInterfaceClient
from ...arena import StreamingCallback as ArenaStreamingCallback
from ...arena import TaskCallback as ArenaTaskCallback
from ...common import ANone
from ...manager import ManagerClient
from ...model import ModelClient
from ...panel import PanelInterfaceClient
from ...panel import StreamingCallback as PanelStreamingCallback
from ...panel import TaskCallback as PanelTaskCallback


@enum.unique
class Part(enum.StrEnum):
    ARENA = enum.auto()
    PANEL = enum.auto()


@enum.unique
class Stage(enum.StrEnum):
    PRE = enum.auto()
    IN = enum.auto()
    POST = enum.auto()


CallbackMessage = tuple[str, Part, Stage, tuple[Any, ...]]


class HasCallbackQueueObject:
    def set_queue(self, queue: "Queue[CallbackMessage]", /) -> None:
        self._queue = queue

    def send(self, *args: Any, session_id: str, part: Part, stage: Stage) -> None:
        self._queue.put_nowait((session_id, part, stage, tuple(args)))


@dataclass(kw_only=True)
class SessionClients:
    model: ModelClient
    arena: ArenaInterfaceClient
    panel: PanelInterfaceClient
    manager: ManagerClient

    async def create(self) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self.model.create())
            tg.create_task(self.arena.create())
            tg.create_task(self.panel.create())
            tg.create_task(self.manager.create())

    async def close(self) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self.model.close())
            tg.create_task(self.arena.close())
            tg.create_task(self.panel.close())
            tg.create_task(self.manager.close())


@dataclass(kw_only=True)
class SessionCallbacks:
    pre_arena: ArenaTaskCallback | None = None
    in_arena: ArenaStreamingCallback | None = None
    post_arena: ArenaTaskCallback | None = None
    pre_panel: PanelTaskCallback | None = None
    in_panel: PanelStreamingCallback | None = None
    post_panel: PanelTaskCallback | None = None

    def __post_init__(self) -> None:
        self._callbacks: dict[tuple[Part, Stage], Callable[..., ANone] | None] = {
            (Part.ARENA, Stage.PRE): self.pre_arena,
            (Part.ARENA, Stage.IN): self.in_arena,
            (Part.ARENA, Stage.POST): self.post_arena,
            (Part.PANEL, Stage.PRE): self.pre_panel,
            (Part.PANEL, Stage.IN): self.in_panel,
            (Part.PANEL, Stage.POST): self.post_panel,
        }

    async def call(self, *args: Any, part: Part, stage: Stage) -> None:
        callback: Callable[..., ANone] | None = self._callbacks[part, stage]
        if callback is not None:
            await callback(*args)


@dataclass(kw_only=True)
class SessionData:
    clients: SessionClients
    callbacks: SessionCallbacks
