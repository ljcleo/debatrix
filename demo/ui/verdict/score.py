from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from nicegui import events, ui

from debatrix.core.common import DebaterName, DimensionName, Verdict

from ..base import BaseUI
from ..util import get_avatar_url
from .comment import CommentUI


@dataclass(kw_only=True)
class DebaterScoreUI(BaseUI[[]]):
    parent: "ScoreUI"
    dimensions_name: dict[DimensionName, str]
    debater_name: DebaterName
    debater_color: str

    def __post_init__(self) -> None:
        super().__init__()
        self._dimensions_name: list[DimensionName] = list(self.dimensions_name)
        self._reset_score()

    @property
    def dimension_data(self) -> list[dict[str, str | int]]:
        return [
            {
                "dimension": dimension_name,
                "name": self.dimensions_name[dimension_name],
                "score": self._dimensions_score[dimension_name],
                "current": int(
                    dimension_name == self.parent.cur_dimension_name
                    and self.debater_name == self.parent.cur_debater_name
                ),
            }
            for dimension_name in self._dimensions_name
        ]

    @property
    def summary_score(self) -> int:
        return self._summary_score

    @summary_score.setter
    def summary_score(self, score: int) -> None:
        self._summary_score = score

    def init_ui(self) -> None:
        with ui.expansion(group="score").classes("w-full") as expansion:
            with expansion.add_slot("header"), ui.row().classes("w-full gap-x-1 items-center"):
                ui.icon(f"img:{get_avatar_url(self.debater_name)}", size="md")
                ui.label(text=self.debater_name).classes("text-2xl")

                with ui.row().classes("ml-auto items-center cursor-pointer").on(
                    "click", self._hdl_row_summary_score
                ):
                    ui.label(text="Summary Score").classes("text-xl")

                    with ui.knob(
                        max=10,
                        step=1,
                        color=self.debater_color,
                        track_color="grey-2",
                        size="xl",
                    ).props("readonly").bind_value_from(self, target_name="summary_score"):
                        ui.label().classes("text-xl font-bold").bind_text_from(
                            self,
                            target_name="summary_score",
                            backward=lambda x: "NA" if x <= 0 or x > 10 else str(x),
                        )

            self._crt_score = ui.echart(
                {
                    "dataset": {"source": self.dimension_data},
                    "xAxis": {"max": 10},
                    "yAxis": {"type": "category", "inverse": True},
                    "visualMap": [
                        {
                            "type": "piecewise",
                            "show": False,
                            "categories": [0, 1],
                            "dimension": 3,
                            "inRange": {"color": ["#5470c6", "#91cc75"]},
                            "outOfRange": {"color": "#fac858"},
                        }
                    ],
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
            self.summary_score = score
        else:
            self._dimensions_score[dimension_name] = score
            self.update_crt_score()

    def _hdl_row_summary_score(self) -> None:
        self.parent.cur_dimension_name = DimensionName("")
        self.parent.cur_debater_name = self.debater_name

    def _hdl_crt_score(self, e: events.EChartPointClickEventArguments) -> None:
        self.parent.cur_dimension_name = self._get_data(e.data, "dimension")
        self.parent.cur_debater_name = self.debater_name

    def _reset_score(self) -> None:
        self._dimensions_score: dict[DimensionName, int] = {
            dimension: 0 for dimension in self._dimensions_name
        }
        self.summary_score = 0

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

        dimensions_display_name: dict[DimensionName, str] = {
            dimension: dimension.capitalize() for dimension in dimensions_name
        }

        real_dimensions_name: list[DimensionName] = [DimensionName("")] + list(
            dimensions_display_name.keys()
        )

        self.cur_dimension_name = DimensionName("")

        debaters_name: list[DebaterName] = list(debaters_bg_color.keys())
        self._debaters_bg_color = debaters_bg_color
        self.cur_debater_name = debaters_name[0]

        self._debate_progress: dict[DebaterName, int] = {
            debater_name: 0 for debater_name in debaters_name
        }

        self._dimensional_judge_started: bool = False

        self._uis_score: dict[DebaterName, DebaterScoreUI] = {
            debater_name: DebaterScoreUI(
                parent=self,
                dimensions_name=dimensions_display_name,
                debater_name=debater_name,
                debater_color=debaters_bg_color[debater_name],
            )
            for debater_name in debaters_name
        }

        self._uis_comment: dict[tuple[DimensionName, DebaterName], CommentUI] = {
            (dimension_name, debater_name): CommentUI(
                dimension_name=dimension_name,
                debater_color=debaters_bg_color[debater_name],
            )
            for dimension_name in real_dimensions_name
            for debater_name in debaters_name
        }

        with ui.splitter(limits=(20, 80), value=60).classes("w-full h-full") as splitter:
            with splitter.before, ui.column().classes("w-full h-full"):
                for debater_name in debaters_name:
                    self._uis_score[debater_name].register_ui()

            with splitter.after, ui.card().classes("w-full h-full"):
                with ui.grid(columns=2).classes("w-full"):
                    self._sel_debater: ui.select = ui.select(
                        debaters_name, label="Debater", on_change=self._switch_chatbox
                    ).classes("col-1")

                    self._sel_dimension: ui.select = ui.select(
                        {
                            dimension: dimensions_display_name.get(dimension, "Summary")
                            for dimension in real_dimensions_name
                        },
                        label="Dimension",
                        on_change=self._switch_chatbox,
                    ).classes("col-1")

                for comment in self._uis_comment.values():
                    comment.register_ui()

                self._sel_debater.bind_value(self, "cur_debater_name")
                self._sel_dimension.bind_value(self, "cur_dimension_name")

    def reset(self) -> None:
        for score in self._uis_score.values():
            score.reset()
        for comment in self._uis_comment.values():
            comment.reset()

    def start_judge(self) -> None:
        for debater in self._debate_progress:
            self._debate_progress[debater] = 0

        self._dimensional_judge_started = False
        for comment in self._uis_comment.values():
            comment.start_judge()

    def start_analysis(
        self, *, dimension_name: DimensionName, debater_name: DebaterName, speech_index: int
    ) -> None:
        if speech_index > self._debate_progress[debater_name]:
            self._debate_progress[debater_name] = speech_index

            self._uis_comment[DimensionName(""), debater_name].start_analysis(
                speech_index=speech_index
            )

        self._uis_comment[dimension_name, debater_name].start_analysis(speech_index=speech_index)

    def update_analysis(
        self, *, dimension_name: DimensionName, debater_name: DebaterName, score: int
    ) -> None:
        self._uis_score[debater_name].update_comment(dimension_name=dimension_name, score=score)

    def start_verdict(self, *, dimension_name: DimensionName) -> None:
        if not self._dimensional_judge_started:
            self._dimensional_judge_started = True

            for key, comment in self._uis_comment.items():
                if key[0] == "":
                    comment.start_verdict(is_dimensional=True)

        is_dimensional: bool = dimension_name != ""

        for key, comment in self._uis_comment.items():
            if key[0] == dimension_name:
                comment.start_verdict(is_dimensional=is_dimensional)

    def update_verdict(self, *, dimension_name: DimensionName, verdict: Verdict) -> None:
        for comment in verdict.debaters_verdict:
            self._uis_score[comment.debater_name].update_comment(
                dimension_name=dimension_name, score=comment.score
            )

            self._uis_comment[dimension_name, comment.debater_name].update_verdict(
                comment=comment.comment
            )

    def _switch_chatbox(self) -> None:
        for key, comment in self._uis_comment.items():
            comment.set_visibility(key == (self.cur_dimension_name, self.cur_debater_name))
        for score in self._uis_score.values():
            score.update_crt_score()
