from abc import abstractmethod
from asyncio import TaskGroup
from collections.abc import Iterable, Mapping
from dataclasses import InitVar, dataclass

from nicegui import ui

from debatrix.core.action import AllPanelActions
from debatrix.core.common import DebateInfo, DebaterName, DimensionName

from ..base import BaseUI
from ..chatbox import DelayedChatBox
from ..util import format_info


@dataclass(kw_only=True)
class PageUI(BaseUI[[]]):
    debaters_bg_color: Mapping[DebaterName, str]
    render_streaming: bool

    def __post_init__(self) -> None:
        super().__init__()
        self._blocks: dict[str, DelayedChatBox] = {}

    @property
    def cur_speech_index(self) -> int:
        return self._cur_speech_index

    @cur_speech_index.setter
    def cur_speech_index(self, index: int) -> None:
        self._cur_speech_index = index

    async def init_chat(self, debate_info: DebateInfo, /) -> None:
        self.cur_speech_index = 0

        async with TaskGroup() as tg:
            for block in self._blocks.values():
                tg.create_task(block.reset(preload=format_info(debate_info, with_info_slide=False)))

    def add_block(
        self,
        key: str,
        title: tuple[str, str | None] | None = None,
        extra_classes: str | None = None,
    ) -> None:
        self._blocks[key] = DelayedChatBox(title=title, extra_classes=extra_classes)

    async def pre_update(
        self, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName
    ) -> None:
        await self._blocks[self.get_block_key(action, dimension_name)].start(
            source=self._get_display_name(dimension_name, debater_name),
            stamp=self.get_stamp(action, dimension_name, debater_name),
            bg_color=self._get_bg_color(debater_name),
            render_streaming=self.render_streaming,
        )

    def update(
        self, action: AllPanelActions, dimension_name: DimensionName, chunk: str, append: bool
    ) -> None:
        chatbox: DelayedChatBox = self._blocks[self.get_block_key(action, dimension_name)]
        if not append:
            chatbox.update(...)

        chatbox.update(chunk)

    async def post_update(self, action: AllPanelActions, dimension_name: DimensionName) -> None:
        await self._blocks[self.get_block_key(action, dimension_name)].stop()

    async def cancel(self) -> None:
        async with TaskGroup() as tg:
            for block in self._blocks.values():
                tg.create_task(block.cancel())

    @abstractmethod
    def get_block_key(self, action: AllPanelActions, dimension_name: DimensionName) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_stamp(
        self, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName
    ) -> str | None:
        raise NotImplementedError()

    def _get_bg_color(self, debater_name: DebaterName) -> str | None:
        return self.debaters_bg_color.get(debater_name)

    def _get_display_name(self, dimension_name: DimensionName, debater_name: DebaterName) -> str:
        name: str = "AI"
        suffix: str = dimension_name.capitalize()

        if suffix == "":
            suffix = "Summary"

        name = f"{name}_{suffix}"
        if debater_name != "":
            name = f"{name}_{debater_name}"

        return name


@dataclass(kw_only=True)
class DimensionalPageUI(PageUI):
    dimensions_name: InitVar[Iterable[DimensionName]]
    is_final: bool

    def __post_init__(self, dimensions_name: Iterable[DimensionName]) -> None:
        super().__post_init__()
        self._dimensions_name: list[DimensionName] = list(dimensions_name)

    def init_ui(self) -> None:
        with ui.grid(columns=10).classes("w-full h-full min-h-[64rem] 2xl:min-h-[40rem]"):
            for dimension in self._dimensions_name:
                self.add_block(dimension, extra_classes="col-span-10 md:col-span-5 2xl:col-span-2")

    def get_block_key(self, action: AllPanelActions, dimension_name: DimensionName) -> str:
        return dimension_name

    def get_stamp(
        self, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName
    ) -> str | None:
        return "After debate" if self.is_final else f"After speech {self.cur_speech_index}"


class MergedPageUI(PageUI):
    def init_ui(self) -> None:
        with ui.grid(columns=1).classes("w-full h-full min-h-[64rem] md:min-h-[40rem]"):
            self.add_block("main", extra_classes="col-span-2 md:col-span-1")

    def get_block_key(self, action: AllPanelActions, dimension_name: DimensionName) -> str:
        return "main"

    def get_stamp(
        self, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName
    ) -> str | None:
        return "After debate"
