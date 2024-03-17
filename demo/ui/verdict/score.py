from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any

from nicegui import events, ui

from debatrix.core.common import DebaterName, DimensionName, Verdict

from ..base import BaseUI
from ..util import get_avatar_url
from .comment import CommentUI


@dataclass(kw_only=True)
class DebaterScoreUI(BaseUI[[]]):
    parent: "ScoreUI"
    dimensions_name: list[DimensionName]
    debater_name: DebaterName
    debater_color: str
    is_first: bool

    def __post_init__(self) -> None:
        super().__init__()
        self._reset_score()

    @property
    def dimension_data(self) -> list[dict[str, str | float]]:
        return [
            {
                "dimension": dimension_name,
                "name": dimension_name.capitalize(),
                "score": max(self._dimensions_score[dimension_name], 0.1),
            }
            for dimension_name in self.dimensions_name
        ]

    @property
    def panel_score(self) -> int:
        return self._panel_score

    @panel_score.setter
    def panel_score(self, score: int) -> None:
        self._panel_score = score

    def init_ui(self) -> None:
        with ui.expansion(group="score", value=self.is_first).classes("w-full") as expansion:
            with expansion.add_slot("header"), ui.row().classes("w-full items-center"):
                ui.icon(f"img:{get_avatar_url(self.debater_name)}", size="3rem").classes(
                    "max-sm:hidden"
                )

                ui.label(text=self.debater_name).classes("text-2xl")

                with ui.row().classes(
                    "p-2 ml-auto rounded-lg items-center cursor-pointer bg-gray-500/50"
                ).on(
                    "click",
                    partial(
                        self.parent.show_comment,
                        dimension_name=DimensionName(""),
                        debater_name=self.debater_name,
                    ),
                ):
                    ui.label(text="Panel Score").classes("text-xl")

                    with ui.knob(
                        max=10,
                        step=1,
                        color=self.debater_color,
                        track_color="grey-2",
                        size="xl",
                    ).props("readonly").bind_value_from(self, target_name="panel_score"):
                        ui.label().classes("text-xl font-bold").bind_text_from(
                            self,
                            target_name="panel_score",
                            backward=lambda x: "NA" if x <= 0 or x > 10 else str(x),
                        )

            self._crt_score = ui.echart(
                {
                    "dataset": {"source": self.dimension_data},
                    "xAxis": {"max": 10},
                    "yAxis": {"type": "category", "inverse": True},
                    "series": [{"type": "bar", "encode": {"x": "score", "y": "name"}}],
                    "tooltip": {"show": True},
                },
                on_point_click=self._hdl_crt_score,
            ).classes("w-full")

    def reset(self) -> None:
        self._reset_score()
        self.update_crt_score()

    def update_comment(self, *, dimension_name: DimensionName, score: int) -> None:
        if dimension_name == "":
            self.panel_score = score
        else:
            self._dimensions_score[dimension_name] = score
            self.update_crt_score()

    async def _hdl_crt_score(self, e: events.EChartPointClickEventArguments) -> None:
        await self.parent.show_comment(
            dimension_name=self._get_data(e.data, "dimension"), debater_name=self.debater_name
        )

    def _reset_score(self) -> None:
        self._dimensions_score: dict[DimensionName, int] = {
            dimension: 0 for dimension in self.dimensions_name
        }

        self.panel_score = 0

    def update_crt_score(self) -> None:
        self._crt_score.options["dataset"]["source"] = self.dimension_data
        self._crt_score.update()

    @staticmethod
    def _get_data(data: Any, key: str, /) -> Any:
        return data[key]


class ScoreUI(BaseUI[Iterable[DimensionName] | None, Mapping[DebaterName, str] | None]):
    @property
    def cur_dimension_name(self) -> DimensionName:
        return self._cur_dimension_name

    @property
    def cur_debater_name(self) -> DebaterName:
        return self._cur_debater_name

    @cur_dimension_name.setter
    def cur_dimension_name(self, dimension_name: DimensionName) -> None:
        self._cur_dimension_name = dimension_name

    @cur_debater_name.setter
    def cur_debater_name(self, debater_name: DebaterName) -> None:
        self._cur_debater_name = debater_name

    def init_ui(
        self,
        dimensions_name: Iterable[DimensionName] | None,
        debaters_bg_color: Mapping[DebaterName, str] | None,
    ) -> None:
        if dimensions_name is None or debaters_bg_color is None:
            return

        self._dimensions_name: list[DimensionName] = list(dimensions_name)
        self._all_dimensions_name: list[DimensionName] = self._dimensions_name + [DimensionName("")]
        self._debaters_bg_color = debaters_bg_color
        self._debaters_name: list[DebaterName] = list(debaters_bg_color.keys())

        self._uis_score: dict[DebaterName, DebaterScoreUI] = {
            debater_name: DebaterScoreUI(
                parent=self,
                dimensions_name=self._dimensions_name,
                debater_name=debater_name,
                debater_color=debaters_bg_color[debater_name],
                is_first=i == 0,
            )
            for i, debater_name in enumerate(self._debaters_name)
        }

        self._uis_comment: dict[tuple[DimensionName, DebaterName], CommentUI] = {
            (dimension_name, debater_name): CommentUI(
                dimension_name=dimension_name,
                debater_color=debaters_bg_color[debater_name],
            )
            for dimension_name in self._all_dimensions_name
            for debater_name in self._debaters_name
        }

        with ui.column().classes("w-full h-full gap-0 overflow-y-auto"):
            for debater_name in self._debaters_name:
                self._uis_score[debater_name].register_ui()

        for dimension_name in self._all_dimensions_name:
            for debater_name in self._debaters_name:
                self._uis_comment[dimension_name, debater_name].register_ui()

    async def show_comment(
        self, *, dimension_name: DimensionName, debater_name: DebaterName
    ) -> None:
        await self._uis_comment[dimension_name, debater_name].show()

    def reset(self) -> None:
        for debater_name in self._debaters_name:
            self._uis_score[debater_name].reset()
            for dimension_name in self._all_dimensions_name:
                self._uis_comment[dimension_name, debater_name].reset()

    def start_judge(self) -> None:
        for comment in self._uis_comment.values():
            comment.start_judge()

    def start_analysis(
        self, *, dimension_name: DimensionName, debater_name: DebaterName, speech_index: int
    ) -> None:
        self._uis_comment[dimension_name, debater_name].start_analysis(speech_index=speech_index)

    def update_analysis(
        self, *, dimension_name: DimensionName, debater_name: DebaterName, score: int
    ) -> None:
        self._uis_score[debater_name].update_comment(dimension_name=dimension_name, score=score)

    def start_verdict(self, *, dimension_name: DimensionName) -> None:
        for key, comment in self._uis_comment.items():
            if key[0] == dimension_name:
                comment.start_verdict(is_dimensional=dimension_name != "")

    def update_verdict(self, *, dimension_name: DimensionName, verdict: Verdict) -> None:
        for comment in verdict.debaters_verdict:
            self._uis_score[comment.debater_name].update_comment(
                dimension_name=dimension_name, score=comment.score
            )

            self._uis_comment[dimension_name, comment.debater_name].update_verdict(
                comment=comment.comment
            )
