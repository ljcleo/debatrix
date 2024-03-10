from dataclasses import dataclass
from typing import Any

from ...api import ServerInfo
from ...core.common import DebaterInfo, DebaterName, Speech
from ...core.component import BaseArena, BaseDebater
from ..interface import ArenaInterfaceClient
from .base import HasInterfaceObject
from .common import QueryStage, TaskCallback


class Debater(HasInterfaceObject, BaseDebater):
    async def reset(self) -> None:
        await self.interface.debater_reset(self.debater_info.name)

    async def poll(self) -> bool:
        return await self.interface.debater_poll(self.debater_info.name)

    async def pre_query(self) -> None:
        await self.callback(stage=QueryStage.PRE, debater_name=self.debater_info.name)

    async def query(self) -> str:
        return await self.interface.debater_query(self.debater_info.name)

    async def update(self, *, speech: Speech) -> None:
        await self.interface.debater_update(self.debater_info.name, speech=speech)


@dataclass(kw_only=True)
class Arena(HasInterfaceObject, BaseArena[Debater]):
    pre_query_callback: TaskCallback | None = None
    post_query_callback: TaskCallback | None = None

    def __post_init__(self):
        self._interface = ArenaInterfaceClient()

    @property
    def interface(self) -> ArenaInterfaceClient:
        return self._interface

    async def create_debater(self, *, index: int, debater_info: DebaterInfo) -> Debater:
        return Debater(parent=self)

    async def post_query(self, speech: Speech | None, /) -> None:
        if speech is not None:
            await self.callback(speech, stage=QueryStage.POST, debater_name=speech.debater_name)
        else:
            await self.callback(speech, stage=QueryStage.PRE, debater_name=DebaterName(""))

    async def callback(self, *args: Any, stage: QueryStage, debater_name: DebaterName) -> None:
        func: TaskCallback | None = None

        if stage == QueryStage.PRE:
            func = self.pre_query_callback
        elif stage == QueryStage.POST:
            func = self.post_query_callback

        await self._callback(*args, func=func, debater_name=debater_name)

    def set_interface_server(self, *, server_info: ServerInfo) -> None:
        self.interface.set_server_info(server_info)

    async def close(self) -> None:
        await self.interface.close()

    @staticmethod
    async def _callback(*args: Any, func: TaskCallback | None, debater_name: DebaterName) -> None:
        if func is not None:
            await func(debater_name, *args)
