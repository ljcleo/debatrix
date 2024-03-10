from asyncio import Task, TaskGroup
from dataclasses import KW_ONLY, dataclass
from pathlib import Path
from socket import create_server, socket
from typing import Any

from fastapi import FastAPI
from nicegui import ui
from uvicorn import Config, Server

from debatrix.core.action import AllPanelActions
from debatrix.core.common import DebateInfo, DebateResult, DebaterName, DimensionName
from debatrix.platform import Platform

from .arena import ArenaUI
from .base import BaseUI
from .config import ConfigUI
from .control import ControlUI
from .detail import DetailUI
from .verdict import VerdictUI


@dataclass
class PlatformUI(BaseUI[[]], Platform):
    _: KW_ONLY
    ui_host: str = "0.0.0.0"
    ui_port: int = 0

    def __post_init__(self, resource_root: Path) -> None:
        super().__init__()
        super().__post_init__(resource_root)

        self.register_ui()
        ui.timer(1.0, self.refresh_config, once=True)

        gui_app = FastAPI(debug=self.debug)
        ui.run_with(gui_app, title="Debatrix Demo", favicon="♎", dark=None)
        self._server = Server(Config(gui_app, log_level="info" if self.log_info else "warning"))

        self._socket: socket = create_server((self.ui_host, self.ui_port), reuse_port=True)
        print("platform ui server at", f"http://{self.ui_host}:{self._socket.getsockname()[1]}")

    def init_ui(self) -> None:
        ui.query(".nicegui-content").classes("h-screen min-h-[72rem] xl:min-h-[48rem]")

        with ui.dialog() as dlg_config, ui.card().classes("w-full h-3/4 gap-y-0 min-h-[24rem]"):
            ConfigUI().register_ui(self)

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

                ControlUI().register_ui(self, dlg_config, dlg_detail)

            with ui.card().classes("col-span-3 xl:col-span-2 h-full gap-y-0"):
                self._ui_verdict = VerdictUI()
                self._ui_verdict.register_ui(None, None)

    async def init_chat(self, info: DebateInfo, /) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self._ui_arena.init_chat(info))
            tg.create_task(self._ui_verdict.init_chat())
            tg.create_task(self._ui_detail.init_chat(info))

    async def pre_arena_query_callback(self, *args: Any, debater_name: DebaterName) -> None:
        self._speech_counter += 1

        async with TaskGroup() as tg:
            tg.create_task(super().pre_arena_query_callback(*args, debater_name=debater_name))

            if debater_name == "":
                tg.create_task(self._ui_arena.end_debate())
            else:
                tg.create_task(
                    self._ui_arena.start_speech(
                        debater_name=debater_name,
                        speech_index=self._speech_counter,
                        bg_color=self._debaters_bg_color[debater_name],
                    )
                )

    async def in_arena_query_callback(
        self, chunk: str | None, *, debater_name: DebaterName
    ) -> None:
        await super().in_arena_query_callback(chunk, debater_name=debater_name)
        if chunk is not None:
            self._ui_arena.update_speech(chunk)

    async def post_arena_query_callback(self, *args: Any, debater_name: DebaterName) -> None:
        async with TaskGroup() as tg:
            tg.create_task(super().post_arena_query_callback(*args, debater_name=debater_name))
            tg.create_task(self._ui_arena.stop_speech())

    async def pre_panel_action_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        async with TaskGroup() as tg:
            tg.create_task(
                super().pre_panel_action_callback(
                    *args, action=action, dimension_name=dimension_name
                )
            )

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

    async def in_panel_action_callback(
        self,
        chat_chunk: tuple[str, str] | None,
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
    ) -> None:
        async with TaskGroup() as tg:
            tg.create_task(
                super().in_panel_action_callback(
                    chat_chunk, action=action, dimension_name=dimension_name
                )
            )

            if chat_chunk is not None:
                source: str
                content: str
                source, content = chat_chunk

                append: bool = (
                    source == "ai" and self._panel_message_incomplete[action, dimension_name]
                )

                tg.create_task(
                    self._ui_verdict.in_panel_action_callback(
                        chat_chunk, action=action, dimension_name=dimension_name
                    )
                )

                if self.record_prompts or source in ("ai", "extra"):
                    tg.create_task(
                        self._ui_detail.in_panel_action_callback(
                            content, append, action=action, dimension_name=dimension_name
                        )
                    )

    async def post_panel_action_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        async with TaskGroup() as tg:
            tg.create_task(
                super().post_panel_action_callback(
                    *args, action=action, dimension_name=dimension_name
                )
            )

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

    async def serve(self) -> None:
        async with TaskGroup() as tg:
            super_task: Task[None] = tg.create_task(super().serve())

            try:
                await self._server.serve(sockets=[self._socket])
            finally:
                print("goodbye platform ui")
                await self._server.shutdown(sockets=[self._socket])
                super_task.cancel()

    async def update_config(self) -> bool:
        updated: bool = await super().update_config()
        if updated:
            self.refresh_ui()

        return updated

    async def select_debate(self, value: str | None) -> None:
        await super().select_debate(value)

        with self._bg_task():
            if self.cur_motion is not None:
                self._ui_verdict.refresh_ui(
                    self._config_buffer_hub.manager.dimensions_name, self._debaters_bg_color
                )

                self._ui_detail.refresh_ui(
                    self._config_buffer_hub.manager.dimensions_name, self._debaters_bg_color
                )
            else:
                self._ui_detail.refresh_ui(None, None)
                self._ui_verdict.refresh_ui(None, None)

        await self._init_debate_ui()

    async def reset_debate(self) -> None:
        if self.is_dirty:
            await self._init_debate_ui()

        await super().reset_debate()

    async def start_debate(self) -> DebateResult | None:
        with self._bg_task():
            await self._ui_verdict.start_judge()

        self._speech_counter: int = 0
        result: DebateResult | None = await super().start_debate()

        if result is None:
            with self._bg_task():
                async with TaskGroup() as tg:
                    tg.create_task(self._ui_arena.cancel())
                    tg.create_task(self._ui_detail.cancel())

        return result

    async def save_record(self) -> str:
        name: str = await super().save_record()
        ui.notify(f"Debate record saved to record/{name}.yml", type="info")
        return name

    async def _init_debate_ui(self) -> None:
        with self._bg_task():
            if self.cur_info is not None:
                await self.init_chat(self.cur_info)
            else:
                await self._ui_arena.reset()
