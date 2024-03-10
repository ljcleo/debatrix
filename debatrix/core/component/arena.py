from abc import abstractmethod
from asyncio import Task, TaskGroup
from random import choice
from typing import Generic, TypeVar

from ..common import DebaterInfo, DebaterName, Speech
from .base import DebateObject
from .interface import CanPoll, CanQuery, CanReset, CanUpdate


class BaseDebater(DebateObject, CanReset, CanPoll, CanQuery[str], CanUpdate):
    @property
    def debater_info(self) -> DebaterInfo:
        return self._debater_info

    @debater_info.setter
    def debater_info(self, debater_info: DebaterInfo) -> None:
        self._debater_info = debater_info


T = TypeVar("T", bound=BaseDebater)


class BaseArena(DebateObject, CanReset, CanQuery[Speech | None], CanUpdate, Generic[T]):
    @property
    def debaters(self) -> tuple[T, ...]:
        return self._debaters

    async def update_info(self) -> None:
        debaters: list[T] = []

        for index, debater_info in enumerate(self.debate_info.all_debaters_info):
            debater: T = await self.create_debater(index=index, debater_info=debater_info)
            debater.debater_info = debater_info
            debaters.append(debater)

        self._debaters: tuple[T, ...] = tuple(debaters)

        self._debater_name_index: dict[DebaterName, int] = {
            debater.debater_info.name: index for index, debater in enumerate(debaters)
        }

    async def reset(self) -> None:
        self._pivot: int = 0

        async with TaskGroup() as tg:
            for debater in self.debaters:
                tg.create_task(debater.reset())

    async def query(self) -> Speech | None:
        if self._pivot >= len(self.debate_info.speech_order):
            return None

        debater_name: DebaterName | None = self.debate_info.speech_order[self._pivot]
        self._pivot += 1

        if debater_name is None:
            async with TaskGroup() as tg:
                poll_tasks: dict[DebaterName, Task[bool]] = {
                    debater.debater_info.name: tg.create_task(debater.poll())
                    for debater in self.debaters
                }

            candidates: list[DebaterName] = [
                debater_name for debater_name, task in poll_tasks.items() if task.result()
            ]

            if len(candidates) == 0:
                return None

            debater_name = choice(candidates)

        return Speech(
            index=0,
            index_by_debater=0,
            debater_name=debater_name,
            content=await self._debaters[self._debater_name_index[debater_name]].query(),
        )

    async def update(self, *, speech: Speech) -> None:
        async with TaskGroup() as tg:
            for debater in self.debaters:
                tg.create_task(debater.update(speech=speech))

    @abstractmethod
    async def create_debater(self, *, index: int, debater_info: DebaterInfo) -> T:
        raise NotImplementedError()
