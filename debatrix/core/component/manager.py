from abc import abstractmethod
from asyncio import Queue, Task, TaskGroup
from typing import Generic, TypeVar

from ..common import DebateInfo, DebateResult, DebaterName, DimensionalVerdict, Speech, Verdict
from .arena import BaseArena
from .base import DebateObject
from .panel import BasePanel

AT = TypeVar("AT", bound=BaseArena)
PT = TypeVar("PT", bound=BasePanel)


class BaseManager(DebateObject, Generic[AT, PT]):
    async def initialize(self) -> None:
        self._arena: AT = await self.create_arena()
        self._panel: PT = await self.create_panel()

    @property
    def debate_info(self) -> DebateInfo:
        return self._debate_info

    @property
    def arena(self) -> AT:
        return self._arena

    @property
    def panel(self) -> PT:
        return self._panel

    async def update_info(self, debate_info: DebateInfo, /) -> None:
        self._debate_info = debate_info
        await self.arena.update_info()

    async def run(self, *, should_summarize: bool) -> DebateResult:
        async with TaskGroup() as tg:
            tg.create_task(self.arena.reset())
            tg.create_task(self.panel.reset())

        queue: Queue[Speech | None] = Queue()
        self._main_counter: int = 0

        self._debater_counter: dict[DebaterName, int] = {
            debater_info.name: 0 for debater_info in self.debate_info.all_debaters_info
        }

        async with TaskGroup() as tg:
            tg.create_task(self._fetch(queue=queue))

            judge_task: Task[DebateResult] = tg.create_task(
                self._judge(queue=queue, should_summarize=should_summarize)
            )

        return judge_task.result()

    async def _fetch(self, *, queue: Queue[Speech | None]) -> None:
        while True:
            speech: Speech | None = await self.arena.query()

            if speech is None:
                queue.put_nowait(None)
                break

            self._main_counter += 1
            self._debater_counter[speech.debater_name] += 1

            speech = Speech(
                index=self._main_counter,
                index_by_debater=self._debater_counter[speech.debater_name],
                debater_name=speech.debater_name,
                content=speech.content,
            )

            queue.put_nowait(speech)
            await self.arena.update(speech=speech)

    async def _judge(self, *, queue: Queue[Speech | None], should_summarize: bool) -> DebateResult:
        speeches: list[Speech] = []

        while True:
            speech: Speech | None = await queue.get()
            if speech is None:
                break

            await self.panel.update(speech=speech)

        dimensional_verdicts: tuple[DimensionalVerdict, ...] = await self.panel.dimensional_judge()
        final_verdict: Verdict | None = None

        if should_summarize:
            final_verdict = await self.panel.summarize(verdicts=dimensional_verdicts)

        return DebateResult(
            speeches=tuple(speeches),
            dimensional_verdicts=dimensional_verdicts,
            final_verdict=final_verdict,
        )

    @abstractmethod
    async def create_arena(self) -> AT:
        raise NotImplementedError()

    @abstractmethod
    async def create_panel(self) -> PT:
        raise NotImplementedError()
