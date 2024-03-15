from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nicegui import app

from debatrix.core.action import AllPanelActions
from debatrix.core.common import DebateResult, DebaterName, DimensionName
from debatrix.platform import Session

from .ui import SessionUI


@dataclass
class UIBasedSession(Session):
    def __post_init__(self) -> None:
        super().__post_init__()
        self._ui = SessionUI()

    async def pre_arena_callback(self, *args: Any, debater_name: DebaterName) -> None:
        await self._ui.pre_arena_callback(debater_name=debater_name)

    async def in_arena_callback(self, chunk: str | None, /, *, debater_name: DebaterName) -> None:
        if chunk is not None:
            await self._ui.in_arena_callback(chunk)

    async def post_arena_callback(self, *args: Any, debater_name: DebaterName) -> None:
        await self._ui.post_arena_query_callback()

    async def pre_panel_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        await self._ui.pre_panel_callback(*args, action=action, dimension_name=dimension_name)

    async def in_panel_callback(
        self,
        chat_chunk: tuple[str, str] | None,
        /,
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
    ) -> None:
        if chat_chunk is not None:
            await self._ui.in_panel_callback(
                chat_chunk,
                action=action,
                dimension_name=dimension_name,
                append=self.recorder.is_append(
                    action=action, dimension_name=dimension_name, chat_chunk=chat_chunk
                ),
                update_detail=self.recorder.need_update(chat_chunk=chat_chunk),
            )

    async def post_panel_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        await self._ui.post_panel_callback(*args, action=action, dimension_name=dimension_name)

    async def setup(self) -> None:
        await super().setup()

        if "state" in app.storage.user:
            await self.set_session_state(app.storage.user["state"])
        else:
            self.cache_session_state()

    async def update_config(self) -> bool:
        updated: bool = await super().update_config()
        self.cache_session_state()

        if updated:
            self._ui.refresh_ui(self)

        return updated

    async def select_debate(self, value: str | None) -> None:
        await super().select_debate(value)

        with self._bg_task():
            await self._ui.select_debate(
                debate_info=self.cur_info,
                dimensions_name=[
                    dimension.name
                    for dimension in self.config_buffer_hub.manager.get_valid_dimensions(
                        self.session_id
                    )
                ],
            )

    async def reset_debate(self) -> None:
        if self.is_dirty:
            await self._ui.reset_debate(debate_info=self.cur_info)

        await super().reset_debate()

    async def start_debate(self) -> DebateResult | None:
        with self._bg_task():
            await self._ui.start_debate()

        result: DebateResult | None = await super().start_debate()

        if result is None:
            with self._bg_task():
                await self._ui.cancel_debate()

        return result

    async def save_record(self) -> Path:
        target: Path = await super().save_record()
        await self._ui.download_record(target=target)
        return target

    def register_ui(self) -> None:
        self._ui.register_ui(self)

    def cache_session_state(self) -> None:
        app.storage.user["state"] = self.session_state
