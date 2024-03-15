from abc import abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import InitVar, dataclass

from nicegui import ui

from debatrix.core.action import AllPanelActions
from debatrix.core.common import DebateInfo, DebaterName, DimensionName

from ..base import BaseUI
from ..chatbox import ChatBox
from ..util import format_info


@dataclass(kw_only=True)
class PageUI(BaseUI[[]]):
    debaters_bg_color: Mapping[DebaterName, str]
    render_streaming: bool

    def __post_init__(self) -> None:
        super().__init__()
        self._blocks: dict[str, ChatBox] = {}
        self._uuids: dict[tuple[AllPanelActions, DimensionName], str] = {}

    @property
    def cur_speech_index(self) -> int:
        return self._cur_speech_index

    @cur_speech_index.setter
    def cur_speech_index(self, index: int) -> None:
        self._cur_speech_index = index

    def reset(self, *, debate_info: DebateInfo) -> None:
        self.cur_speech_index = 0
        for block in self._blocks.values():
            block.reset(preload=format_info(debate_info, with_info_slide=False))

    def add_block(
        self,
        key: str,
        /,
        *,
        title: tuple[str, str | None] | None = None,
        extra_classes: str | None = None,
    ) -> None:
        self._blocks[key] = ChatBox(title=title, extra_classes=extra_classes)

    def pre_update(
        self, *, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName
    ) -> None:
        self._uuids[action, dimension_name] = self._get_block(
            action, dimension_name
        ).assign_message(
            source=self._get_display_name(dimension_name, debater_name),
            stamp=self.get_stamp(action, dimension_name, debater_name),
            bg_color=self._get_bg_color(debater_name),
        )

    def update(
        self, chunk: str, /, *, action: AllPanelActions, dimension_name: DimensionName, append: bool
    ) -> None:
        chatbox: ChatBox = self._get_block(action, dimension_name)
        uuid: str = self._uuids[action, dimension_name]

        if not append:
            chatbox.append_to_message(uuid, chunk=...)

        chatbox.append_to_message(uuid, chunk=chunk)

    def post_update(self, *, action: AllPanelActions, dimension_name: DimensionName) -> None:
        self._get_block(action, dimension_name).cut_message(self._uuids[action, dimension_name])
        del self._uuids[action, dimension_name]

    @abstractmethod
    def get_block_key(self, action: AllPanelActions, dimension_name: DimensionName, /) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_stamp(
        self, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName, /
    ) -> str | None:
        raise NotImplementedError()

    def _get_block(self, action: AllPanelActions, dimension_name: DimensionName, /) -> ChatBox:
        return self._blocks[self.get_block_key(action, dimension_name)]

    def _get_bg_color(self, debater_name: DebaterName, /) -> str | None:
        return self.debaters_bg_color.get(debater_name)

    def _get_display_name(self, dimension_name: DimensionName, debater_name: DebaterName, /) -> str:
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
        n_dim: int = len(self._dimensions_name)
        n_col: int = n_dim << 1

        with ui.grid(columns=n_col).classes("w-full h-full min-h-[64rem] 2xl:min-h-[40rem]"):
            for dimension in self._dimensions_name:
                self.add_block(
                    dimension,
                    extra_classes=f"col-span-{n_col} md:col-span-{max(n_dim, 2)} 2xl:col-span-2",
                )

    def get_block_key(self, action: AllPanelActions, dimension_name: DimensionName, /) -> str:
        return dimension_name

    def get_stamp(
        self, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName, /
    ) -> str | None:
        return "After debate" if self.is_final else f"After speech {self.cur_speech_index}"


class MergedPageUI(PageUI):
    def init_ui(self) -> None:
        with ui.grid(columns=1).classes("w-full h-full min-h-[64rem] md:min-h-[40rem]"):
            self.add_block("main", extra_classes="col-span-2 md:col-span-1")

    def get_block_key(self, action: AllPanelActions, dimension_name: DimensionName, /) -> str:
        return "main"

    def get_stamp(
        self, action: AllPanelActions, dimension_name: DimensionName, debater_name: DebaterName, /
    ) -> str | None:
        return "After debate"
