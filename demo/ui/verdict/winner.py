from collections.abc import Iterable
from dataclasses import dataclass
from functools import partial

from nicegui import ui

from debatrix.core.common import DebaterName, DimensionName, Verdict

from ..base import BaseUI
from ..util import get_avatar_url
from .comment import CommentUI


@dataclass(kw_only=True)
class DimensionalWinnerUI(BaseUI[[]]):
    dimension_name: DimensionName

    def __post_init__(self) -> None:
        super().__init__()
        self._status: str | None = None
        self._winner: DebaterName | None = None

    def init_ui(self) -> None:
        if self.dimension_name == "":
            with ui.column().classes("w-full items-center") as container:
                ui.label("Panel Main Judge").classes("text-2xl")
                ui.separator()
        else:
            with ui.row().classes("w-full h-full items-center") as container:
                ui.label(self.dimension_name.capitalize()).classes("w-28 text-2xl")
                ui.separator().props("vertical")

        with container:
            self._ui_status: ui.label = (
                ui.label()
                .classes("grow text-right text-lg")
                .bind_text_from(self, target_name="_status")
                .bind_visibility_from(self, target_name="_winner", backward=lambda x: x is None)
            )

            self._ui_winner: ui.row = (
                ui.row()
                .classes("grow items-center justify-end")
                .bind_visibility_from(self, target_name="_winner", backward=lambda x: x is not None)
            )

    def reset(self) -> None:
        self.set_status("Waiting for the debate to start ...")
        self.set_winner(None)

    def set_status(self, status: str | None, /) -> None:
        self._status = status

    def set_winner(self, winner: DebaterName | None, /) -> None:
        self._winner = winner
        self._ui_winner.clear()

        if winner is not None:
            is_panel: bool = self.dimension_name == ""
            text_size: str = "text-4xl" if is_panel else "text-2xl"
            icon_size: str = "4rem" if is_panel else "3rem"

            is_tie: bool = winner == ""
            text: str = "It's a tie!" if is_tie else f"Winner: {winner}"
            icon: str = "balance" if is_tie else f"img:{get_avatar_url(winner)}"

            with self._ui_winner:
                ui.label(text).classes(text_size)
                ui.icon(icon, size=icon_size, color=None).classes("max-sm:hidden")


class WinnerUI(BaseUI[Iterable[DimensionName] | None, Iterable[DebaterName] | None]):
    def init_ui(
        self,
        dimensions_name: Iterable[DimensionName] | None,
        debaters: Iterable[DebaterName] | None,
    ) -> None:
        if dimensions_name is None or debaters is None:
            return

        self._dimensions_name: list[DimensionName] = list(dimensions_name)
        self._all_dimensions_name: list[DimensionName] = self._dimensions_name + [DimensionName("")]
        self._debaters_name: list[DebaterName] = list(debaters)

        self._uis_winner: dict[DimensionName, DimensionalWinnerUI] = {
            dimension: DimensionalWinnerUI(dimension_name=dimension)
            for dimension in self._all_dimensions_name
        }

        self._uis_comment: dict[DimensionName, CommentUI] = {
            dimension_name: CommentUI(dimension_name=dimension_name)
            for dimension_name in self._all_dimensions_name
        }

        with ui.column().classes("w-full h-full"):
            with ui.column().classes("w-full grow gap-0 overflow-y-auto"):
                for dimension_name in self._dimensions_name:
                    with ui.card().classes("w-full h-24 cursor-pointer").on(
                        "click", partial(self.show_comment, dimension_name=dimension_name)
                    ):
                        self._uis_winner[dimension_name].register_ui()

            with ui.card().classes("h-40 w-full cursor-pointer").on(
                "click", partial(self.show_comment, dimension_name=DimensionName(""))
            ):
                self._uis_winner[DimensionName("")].register_ui()

        for dimension_name in self._all_dimensions_name:
            self._uis_comment[dimension_name].register_ui()

    async def show_comment(self, *, dimension_name: DimensionName) -> None:
        await self._uis_comment[dimension_name].show()

    def reset(self) -> None:
        for dimension_name in self._all_dimensions_name:
            self._uis_winner[dimension_name].reset()
            self._uis_comment[dimension_name].reset()

    def start_judge(self) -> None:
        for dimension_name in self._all_dimensions_name:
            self._uis_winner[dimension_name].set_status(
                "Waiting for dimensional judges ..." if dimension_name == "" else "Ready to judge."
            )

            self._uis_comment[dimension_name].start_judge()

    def start_analysis(self, *, dimension_name: DimensionName, speech_index: int) -> None:
        self._uis_winner[dimension_name].set_status(f"Judging speech {speech_index} ...")
        self._uis_comment[dimension_name].start_analysis(speech_index=speech_index)

    def start_verdict(self, *, dimension_name: DimensionName) -> None:
        self._uis_winner[dimension_name].set_status("Preparing final verdict ...")
        self._uis_comment[dimension_name].start_verdict(is_dimensional=dimension_name != "")

    def update_verdict(self, *, dimension_name: DimensionName, verdict: Verdict) -> None:
        winner: DebaterName = verdict.winner_verdict.winner
        if winner not in self._debaters_name:
            winner = DebaterName("")

        self._uis_winner[dimension_name].set_winner(winner)
        self._uis_comment[dimension_name].update_verdict(comment=verdict.winner_verdict.comment)
