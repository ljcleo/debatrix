from asyncio import TaskGroup
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from nicegui import ui

from debatrix.core.action import AllPanelActions
from debatrix.core.common import DebateInfo, DebaterName, DimensionName
from debatrix.platform import Session

from .arena import ArenaUI
from .base import BaseUI
from .config import ConfigUI
from .control import ControlUI
from .detail import DetailUI
from .verdict import VerdictUI


class SessionUI(BaseUI[Session]):
    def init_ui(self, session: Session) -> None:
        ui.query(".nicegui-content").classes("h-screen min-h-[72rem] xl:min-h-[48rem]")

        with ui.dialog() as dlg_config, ui.card().classes("w-full h-3/4 gap-y-0 min-h-[24rem]"):
            ConfigUI().register_ui(session)

        with ui.dialog().props("full-width full-height") as dlg_detail, ui.card().classes(
            "gap-y-0"
        ):
            self._ui_detail = DetailUI()
            self._ui_detail.register_ui(None, None)

        with ui.grid(columns=3).classes("w-full h-full lg:px-16 lg:py-8"):
            with ui.card().classes("col-span-3 xl:col-span-1 h-full items-center"):
                with ui.column().classes("w-full grow"):
                    self._ui_arena = ArenaUI()
                    self._ui_arena.register_ui()

                ControlUI().register_ui(session, dlg_config, dlg_detail)

            with ui.card().classes("col-span-3 xl:col-span-2 h-full gap-y-0"):
                self._ui_verdict = VerdictUI()
                self._ui_verdict.register_ui(None, None)

    async def init_chat(self, info: DebateInfo, /) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self._ui_arena.init_chat(info))
            tg.create_task(self._ui_verdict.init_chat())
            tg.create_task(self._ui_detail.init_chat(info))

    async def pre_arena_callback(self, *, debater_name: DebaterName) -> None:
        self._speech_counter += 1

        if debater_name == "":
            await self._ui_arena.end_debate()
        else:
            await self._ui_arena.start_speech(
                debater_name=debater_name,
                speech_index=self._speech_counter,
                bg_color=self._debaters_bg_color[debater_name],
            )

    async def in_arena_callback(self, chunk: str) -> None:
        self._ui_arena.update_speech(chunk)

    async def post_arena_query_callback(self) -> None:
        await self._ui_arena.stop_speech()

    async def pre_panel_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        async with TaskGroup() as tg:
            tg.create_task(
                self._ui_verdict.pre_panel_action_callback(
                    *args, action=action, dimension_name=dimension_name
                )
            )

            tg.create_task(
                self._ui_detail.pre_panel_action_callback(
                    *args, action=action, dimension_name=dimension_name
                )
            )

    async def in_panel_callback(
        self,
        chat_chunk: tuple[str, str],
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
        append: bool,
        update_detail: bool,
    ) -> None:
        async with TaskGroup() as tg:
            tg.create_task(
                self._ui_verdict.in_panel_action_callback(
                    chat_chunk, action=action, dimension_name=dimension_name
                )
            )

            if update_detail:
                tg.create_task(
                    self._ui_detail.in_panel_action_callback(
                        chat_chunk[1], append, action=action, dimension_name=dimension_name
                    )
                )

    async def post_panel_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        async with TaskGroup() as tg:
            tg.create_task(
                self._ui_verdict.post_panel_action_callback(
                    *args, action=action, dimension_name=dimension_name
                )
            )

            tg.create_task(
                self._ui_detail.post_panel_action_callback(
                    *args, action=action, dimension_name=dimension_name
                )
            )

    async def select_debate(
        self, *, debate_info: DebateInfo | None, dimensions_name: Iterable[DimensionName]
    ) -> None:
        if debate_info is not None:
            palette: tuple[str, ...] = ("primary", "secondary", "accent", "warning", "info")

            self._debaters_bg_color: dict[DebaterName, str] = {
                debater_info.name: palette[index % len(palette)]
                for index, debater_info in enumerate(debate_info.all_debaters_info)
            }

            self._ui_verdict.refresh_ui(dimensions_name, self._debaters_bg_color)
            self._ui_detail.refresh_ui(dimensions_name, self._debaters_bg_color)
        else:
            self._ui_detail.refresh_ui(None, None)
            self._ui_verdict.refresh_ui(None, None)

        await self._init_debate_ui(debate_info=debate_info)

    async def reset_debate(self, *, debate_info: DebateInfo | None) -> None:
        await self._init_debate_ui(debate_info=debate_info)

    async def start_debate(self) -> None:
        self._speech_counter: int = 0
        await self._ui_verdict.start_judge()

    async def cancel_debate(self) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self._ui_arena.cancel())
            tg.create_task(self._ui_detail.cancel())

    async def download_record(self, *, target: Path) -> None:
        ui.notify("Debate record saved, start downloading ...", type="info")
        ui.download(target)

    async def _init_debate_ui(self, *, debate_info: DebateInfo | None) -> None:
        if debate_info is not None:
            await self.init_chat(debate_info)
        else:
            await self._ui_arena.reset()
