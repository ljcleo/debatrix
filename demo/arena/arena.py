from debatrix.core.common import DebateInfo, DebaterName

from ..base import BaseUI, DelayedChatBox
from ..util import format_info


class ArenaUI(BaseUI[[]]):
    def init_ui(self) -> None:
        self._cht_debate = DelayedChatBox(title=("Debate", "forum"), extra_classes="min-h-[24rem]")

    async def init_chat(self, debate_info: DebateInfo, /) -> None:
        await self._cht_debate.reset(preload=format_info(debate_info))

    async def reset(self) -> None:
        await self._cht_debate.reset()

    async def start_speech(
        self, *, debater_name: DebaterName, speech_index: int, bg_color: str | None = None
    ) -> None:
        await self._cht_debate.start(
            source=debater_name,
            stamp=f"Speech {speech_index}",
            bg_color=bg_color,
            render_streaming=True,
        )

    def update_speech(self, chunk: str) -> None:
        self._cht_debate.update(chunk)

    async def stop_speech(self) -> None:
        await self._cht_debate.stop()

    async def end_debate(self) -> None:
        await self._cht_debate.insert(
            ["The debate ends. Thank you debaters!"], stamp="After debate", render_streaming=False
        )

    async def cancel(self) -> None:
        await self._cht_debate.cancel()
