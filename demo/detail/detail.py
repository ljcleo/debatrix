import enum
from asyncio import TaskGroup
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from nicegui import ui

from debatrix.core.action import AllPanelActions, JudgeAction, PanelAction
from debatrix.core.common import DebateInfo, DebaterName, DimensionName, Speech

from ..base import BaseUI
from .page import DimensionalPageUI, MergedPageUI, PageUI


class PageFlag(enum.Flag):
    NONE = 0
    MERGED = enum.auto()
    FINAL = enum.auto()


@dataclass
class PageInfo:
    action: AllPanelActions
    title: str
    icon: str
    flags: PageFlag = PageFlag.NONE


class DetailUI(BaseUI[Iterable[DimensionName] | None, Mapping[DebaterName, str] | None]):
    def __init__(self) -> None:
        super().__init__()

        self._pages_info: list[PageInfo] = [
            PageInfo(PanelAction.SUMMARIZE, "General", "gavel", PageFlag.MERGED | PageFlag.FINAL),
            PageInfo(JudgeAction.JUDGE, "Dimensional", "grid_view", PageFlag.FINAL),
            PageInfo(JudgeAction.UPDATE, "Analyses", "pending"),
        ]

        self._action_page_info: dict[AllPanelActions, PageInfo] = {
            info.action: info for info in self._pages_info
        }

        self._action_active_counter: dict[AllPanelActions, int] = {
            info.action: 0 for info in self._pages_info
        }

    def init_ui(
        self,
        dimensions_name: Iterable[DimensionName] | None,
        debaters_bg_color: Mapping[DebaterName, str] | None,
    ) -> None:
        if dimensions_name is None:
            dimensions_name = []
        if debaters_bg_color is None:
            debaters_bg_color = {}

        self._pages: dict[AllPanelActions, PageUI] = {}

        for info in self._pages_info:
            if PageFlag.MERGED in info.flags:
                self._pages[info.action] = MergedPageUI(
                    debaters_bg_color=debaters_bg_color, render_streaming=False
                )
            else:
                self._pages[info.action] = DimensionalPageUI(
                    debaters_bg_color=debaters_bg_color,
                    render_streaming=False,
                    dimensions_name=dimensions_name,
                    is_final=PageFlag.FINAL in info.flags,
                )

        self._page_badge: dict[AllPanelActions, ui.badge] = {}

        with ui.tabs().props("dense").classes("w-full mb-0") as self._tabs:
            for index, info in enumerate(self._pages_info):
                with ui.tab(str(index), label=info.title, icon=info.icon):
                    self._page_badge[info.action] = (
                        ui.badge(color="warning")
                        .props("rounded floating")
                        .bind_visibility_from(
                            self._action_active_counter, target_name=info.action, backward=bool
                        )
                    )

        with ui.tab_panels(self._tabs, value="0").classes("w-full grow"):
            for index, info in enumerate(self._pages_info):
                with ui.tab_panel(str(index)):
                    self._pages[info.action].register_ui()

    async def init_chat(self, debate_info: DebateInfo, /) -> None:
        async with TaskGroup() as tg:
            for page in self._pages.values():
                tg.create_task(page.init_chat(debate_info))

        self._tabs.set_value("0")

    async def pre_panel_action_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        if action not in self._pages.keys():
            return

        debater_name = DebaterName("")

        if action == JudgeAction.UPDATE:
            speech: Speech = args[0]
            debater_name = speech.debater_name
            self._pages[action].cur_speech_index = speech.index

        self._action_active_counter[action] += 1
        await self._pages[action].pre_update(action, dimension_name, debater_name)

    async def in_panel_action_callback(
        self, chunk: str, append: bool, *, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        if action not in self._pages.keys():
            return

        self._pages[action].update(action, dimension_name, chunk, append)

    async def post_panel_action_callback(
        self, *_: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        if action not in self._pages.keys():
            return

        await self._pages[action].post_update(action, dimension_name)
        self._action_active_counter[action] -= 1

    async def cancel(self) -> None:
        async with TaskGroup() as tg:
            for action, page in self._pages.items():
                tg.create_task(page.cancel())
                self._action_active_counter[action] = 0
