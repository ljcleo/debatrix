from abc import abstractmethod
from asyncio import Task, TaskGroup
from collections.abc import Iterable
from typing import Generic, TypeVar

from ..common import DimensionalVerdict, DimensionInfo, Speech, Verdict
from .base import DebateObject
from .interface import CanJudge, CanReset, CanSummarize, CanUpdate


class BaseJudge(DebateObject, CanReset, CanUpdate, CanJudge):
    @property
    def dimension(self) -> DimensionInfo:
        return self._dimension

    @dimension.setter
    def dimension(self, dimension: DimensionInfo) -> None:
        self._dimension = dimension


T = TypeVar("T", bound=BaseJudge)


class BasePanel(DebateObject, CanReset, CanUpdate, CanSummarize, Generic[T]):
    @property
    def dimensions(self) -> tuple[DimensionInfo, ...]:
        return self._dimensions

    @property
    def judges(self) -> tuple[T, ...]:
        return self._judges

    async def set_dimensions(self, dimensions: Iterable[DimensionInfo], /) -> None:
        self._dimensions: tuple[DimensionInfo, ...] = tuple(dimensions)

        await self.create_panel()
        judges: list[T] = []

        for dimension in self.dimensions:
            judge: T = await self.create_judge(dimension=dimension)
            judge.dimension = dimension
            judges.append(judge)

        self._judges = tuple(judges)

    async def reset(self) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self.reset_panel())
            for judge in self.judges:
                tg.create_task(judge.reset())

    async def update(self, *, speech: Speech) -> None:
        async with TaskGroup() as tg:
            for judge in self.judges:
                tg.create_task(judge.update(speech=speech))

    async def dimensional_judge(self) -> tuple[DimensionalVerdict, ...]:
        async with TaskGroup() as tg:
            judge_tasks: list[Task[Verdict]] = [
                tg.create_task(judge.judge()) for judge in self.judges
            ]

        return tuple(
            DimensionalVerdict(dimension=judge.dimension, verdict=task.result())
            for judge, task in zip(self.judges, judge_tasks)
        )

    @abstractmethod
    async def create_panel(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def create_judge(self, *, dimension: DimensionInfo) -> T:
        raise NotImplementedError()

    @abstractmethod
    async def reset_panel(self) -> None:
        raise NotImplementedError()
