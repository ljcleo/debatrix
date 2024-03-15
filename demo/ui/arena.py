from debatrix.core.common import DebateInfo, DebaterName

from .base import BaseUI
from .chatbox import ChatBox
from .util import format_info


class ArenaUI(BaseUI[[]]):
    def init_ui(self) -> None:
        self._cht_debate = ChatBox(title=("Debate", "forum"), extra_classes="min-h-[24rem]")

    def reset(self, *, debate_info: DebateInfo | None = None) -> None:
        self._cht_debate.reset(preload=None if debate_info is None else format_info(debate_info))

    def start_speech(
        self, *, debater_name: DebaterName, speech_index: int, bg_color: str | None = None
    ) -> None:
        self._uuid: str = self._cht_debate.assign_message(
            source=debater_name, stamp=f"Speech {speech_index}", bg_color=bg_color
        )

    def update_speech(self, chunk: str) -> None:
        self._cht_debate.append_to_message(self._uuid, chunk=chunk)

    def stop_speech(self) -> None:
        self._cht_debate.cut_message(self._uuid)

    def end_debate(self) -> None:
        self._cht_debate.insert(["The debate ends. Thank you debaters!"], stamp="After debate")
