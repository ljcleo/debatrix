from asyncio import TaskGroup
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import partial
from operator import not_

from nicegui import ui

from debatrix.core.common import DebaterName, DimensionName, Verdict

from ..base import BaseUI
from ..util import get_avatar_url
from .comment import CommentUI


@dataclass(kw_only=True)
class DebaterAwardUI(BaseUI[[]]):
    parent: "WinnerUI"
    debater_name: DebaterName
    dimensions_name: Mapping[DimensionName, str]

    def __post_init__(self) -> None:
        super().__init__()
        self._is_valid_debater: bool = self.debater_name != ""

        self._dimension_stat: dict[DimensionName, bool] = {
            dimension: False for dimension in self.dimensions_name.keys()
        }

    def init_ui(self) -> None:
        with ui.grid(columns=1).classes("w-full items-stretch"):
            with ui.column().classes("w-full items-center"):
                if self._is_valid_debater:
                    ui.avatar(f"img:{get_avatar_url(self.debater_name)}", size="8rem", color=None)
                    ui.label(self.debater_name).classes("text-2xl")
                else:
                    ui.avatar("balance", size="8rem", color=None)
                    ui.label("Tie?").classes("text-2xl")

            self._btns_dimension: dict[DimensionName, ui.button] = {}
            self._btns_fake: dict[DimensionName, ui.button] = {}

            for dimension, name in self.dimensions_name.items():
                self._btns_dimension[dimension] = (
                    ui.button(name, on_click=partial(self._hdl_btn_dimension, dimension))
                    .props('size="lg"')
                    .bind_visibility_from(self._dimension_stat, target_name=dimension)
                )

                self._btns_fake[dimension] = (
                    ui.button(
                        name, on_click=partial(self._hdl_btn_dimension, dimension), color=None
                    )
                    .props('size="lg"')
                    .classes("text-slate-500/50")
                    .bind_visibility_from(
                        self._dimension_stat, target_name=dimension, backward=not_
                    )
                )

    async def init_chat(self) -> None:
        for dimension in self._dimension_stat.keys():
            self._dimension_stat[dimension] = False

    def toggle_dimension(self, dimension_name: DimensionName) -> None:
        self._dimension_stat[dimension_name] = not self._dimension_stat[dimension_name]

    def _hdl_btn_dimension(self, dimension_name: DimensionName, /) -> None:
        self.parent.cur_dimension_name = dimension_name


class WinnerUI(BaseUI[Iterable[DimensionName] | None, Iterable[DebaterName] | None]):
    @property
    def cur_dimension_name(self) -> DimensionName:
        return self._cur_dimension_name

    @property
    def winner(self) -> DebaterName | None:
        return self._winner

    @cur_dimension_name.setter
    def cur_dimension_name(self, dimension_name: DimensionName) -> None:
        self._cur_dimension_name = dimension_name

    @winner.setter
    def winner(self, winner: DebaterName | None) -> None:
        self._winner = winner

    def init_ui(
        self,
        dimensions_name: Iterable[DimensionName] | None,
        debaters: Iterable[DebaterName] | None,
    ) -> None:
        if dimensions_name is None or debaters is None:
            return

        dimensions_display_name: dict[DimensionName, str] = {
            dimension: dimension.capitalize() for dimension in dimensions_name
        }

        real_dimensions_name: list[DimensionName] = [DimensionName("")] + list(
            dimensions_display_name.keys()
        )

        self.cur_dimension_name = real_dimensions_name[0]

        all_debaters: list[DebaterName] = [DebaterName(""), *debaters]
        self.winner = None

        self._debate_progress: int = 0
        self._dimensional_judge_started: bool = False

        self._uis_award: dict[DebaterName, DebaterAwardUI] = {
            debater_name: DebaterAwardUI(
                parent=self, debater_name=debater_name, dimensions_name=dimensions_display_name
            )
            for debater_name in all_debaters
        }

        self._uis_comment: dict[DimensionName, CommentUI] = {
            dimension: CommentUI(dimension_name=dimension) for dimension in real_dimensions_name
        }

        with ui.splitter(limits=(20, 80), value=60).classes("w-full h-full") as splitter:
            with splitter.before, ui.column().classes("w-full h-full"):
                with ui.grid(columns=len(all_debaters)).classes("w-full grow"):
                    for debater_name in all_debaters:
                        with ui.card().classes("w-full h-full"):
                            self._uis_award[debater_name].register_ui()

                with ui.card().classes("w-full items-center"):
                    ui.label("The final winner is ...").classes("text-xl")

                    self._btn_winner: ui.button = (
                        ui.button(on_click=self._hdl_btn_winner)
                        .props('size="xl"')
                        .classes("min-w-[8rem]")
                        .bind_text_from(self, target_name="winner")
                        .bind_visibility_from(
                            self, target_name="winner", backward=lambda x: x is not None
                        )
                    )

                    self._btn_fake: ui.button = (
                        ui.button(on_click=self._hdl_btn_winner, color=None)
                        .props('size="xl"')
                        .classes("min-w-[8rem]")
                        .bind_visibility_from(
                            self, target_name="winner", backward=lambda x: x is None
                        )
                    )

            with splitter.after, ui.card().classes("w-full h-full"):
                self._sel_dimension: ui.select = ui.select(
                    {
                        dimension: dimensions_display_name.get(dimension, "Summary")
                        for dimension in real_dimensions_name
                    },
                    label="Dimension",
                    on_change=self._switch_chatbox,
                ).classes("w-full")

                for comment in self._uis_comment.values():
                    comment.register_ui()

                self._sel_dimension.bind_value(self, "cur_dimension_name")

    async def init_chat(self) -> None:
        async with TaskGroup() as tg:
            for award in self._uis_award.values():
                tg.create_task(award.init_chat())
            for comment in self._uis_comment.values():
                tg.create_task(comment.init_chat())

        self.winner = None

    async def start_judge(self) -> None:
        self._debate_progress = 0
        self._dimensional_judge_started = False

        async with TaskGroup() as tg:
            for comment in self._uis_comment.values():
                tg.create_task(comment.start_judge())

    async def start_analysis(self, *, dimension_name: DimensionName, speech_index: int) -> None:
        if speech_index > self._debate_progress:
            self._debate_progress = speech_index
            await self._uis_comment[DimensionName("")].start_analysis(speech_index=speech_index)

        await self._uis_comment[dimension_name].start_analysis(speech_index=speech_index)

    async def start_verdict(self, *, dimension_name: DimensionName) -> None:
        if not self._dimensional_judge_started:
            self._dimensional_judge_started = True
            await self._uis_comment[DimensionName("")].start_verdict(is_dimensional=True)

        await self._uis_comment[dimension_name].start_verdict(is_dimensional=dimension_name != "")

    async def update_verdict(self, *, dimension_name: DimensionName, verdict: Verdict) -> None:
        await self._uis_comment[dimension_name].update_verdict(
            comment=verdict.winner_verdict.comment
        )

        if dimension_name == "":
            self.winner = verdict.winner_verdict.winner
        else:
            self._uis_award.get(
                verdict.winner_verdict.winner, self._uis_award[DebaterName("")]
            ).toggle_dimension(dimension_name)

    def _hdl_btn_winner(self) -> None:
        self.cur_dimension_name = DimensionName("")

    def _switch_chatbox(self) -> None:
        for key, comment in self._uis_comment.items():
            comment.set_visibility(key == self.cur_dimension_name)
