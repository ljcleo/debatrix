from dataclasses import dataclass

from debatrix.core.common import DimensionName

from ..base import BaseUI
from ..chatbox import ChatBox


@dataclass(kw_only=True)
class CommentUI(BaseUI[[]]):
    dimension_name: DimensionName
    debater_color: str | None = None

    def __post_init__(self) -> None:
        super().__init__()

        suffix: str = self.dimension_name.capitalize()
        if suffix == "":
            suffix = "Summary"

        self._display_name: str = f"AI_{suffix}"

    def init_ui(self) -> None:
        self._cht_comment = ChatBox()

    def set_visibility(self, visible: bool, /) -> None:
        self._cht_comment.set_visibility(visible)

    def reset(self) -> None:
        self._cht_comment.reset()

    def start_judge(self) -> None:
        self._cht_comment.insert(["The judge is ready."], stamp="Before debate")

    def start_analysis(self, *, speech_index: int) -> None:
        self._cht_comment.insert(
            [f"Judging speech {speech_index} ..."],
            source=self._display_name,
            stamp=f"After speech {speech_index}",
            bg_color=self.debater_color,
        )

    def start_verdict(self, *, is_dimensional: bool) -> None:
        self._cht_comment.insert(
            [f"Preparing {'dimensional' if is_dimensional else 'summarized'} verdict ..."],
            source=self._display_name,
            stamp="After debate",
            bg_color=self.debater_color,
        )

    def update_verdict(self, *, comment: str) -> None:
        self._cht_comment.insert(
            [comment],
            source=self._display_name,
            stamp="Final judgment",
            bg_color=self.debater_color,
        )
