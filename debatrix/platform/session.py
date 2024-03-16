from asyncio import CancelledError, Event, Task, TaskGroup
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..core.action import AllPanelActions, JudgeAction, PanelAction
from ..core.common import DebateInfo, DebateResult, DebaterName, DimensionName
from ..manager import ManagerClient
from .buffer import ConfigBuffer
from .callback import CallbackHub, CallbackStage
from .process import ProcessHub
from .record import Recorder, RecorderHub
from .resource import ResourceHub


@dataclass(kw_only=True)
class Session:
    resource_hub: ResourceHub
    process_hub: ProcessHub
    recorder_hub: RecorderHub
    config_buffer: ConfigBuffer
    callback_hub: CallbackHub

    def __post_init__(self) -> None:
        self._cur_motion: str | None = None
        self._cur_info: DebateInfo | None = None

        self._can_start: bool = False
        self._num_bg_task: int = 0
        self._num_running_debate: int = 0

        self._running_debate: Task[DebateResult] | None = None
        self._panel_done_countdown: int = 0
        self._all_arena_callback_done = Event()
        self._all_panel_callback_done = Event()

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def recorder(self) -> Recorder:
        return self.recorder_hub.get(self.session_id)

    @property
    def is_config_enabled(self) -> bool:
        return not self._num_bg_task > 0

    @property
    def is_debate_loaded(self) -> bool:
        return self._can_start

    @property
    def is_control_enabled(self) -> bool:
        return self._can_start and not self._num_bg_task > 0

    @property
    def is_start_stop_toggled(self) -> bool:
        return self._num_running_debate > 0

    @property
    def is_dirty(self) -> bool:
        return len(self.recorder.records) > 0 or self._running_debate is not None

    @property
    def motions(self) -> list[tuple[str, str]]:
        return self.resource_hub.motion.all_motions

    @property
    def cur_motion(self) -> str | None:
        return self._cur_motion

    @property
    def cur_info(self) -> DebateInfo | None:
        return self._cur_info

    @property
    def config_data(self) -> Any:
        return self._config_data

    async def pre_arena_callback(self, *args: Any, debater_name: DebaterName) -> None:
        pass

    async def in_arena_callback(self, chunk: str | None, /, *, debater_name: DebaterName) -> None:
        pass

    async def post_arena_callback(self, *args: Any, debater_name: DebaterName) -> None:
        pass

    async def pre_panel_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        pass

    async def in_panel_callback(
        self,
        chat_chunk: tuple[str, str] | None,
        /,
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
    ) -> None:
        pass

    async def post_panel_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        pass

    async def setup(self) -> None:
        self._session_id: str = uuid4().hex
        self.recorder_hub.create(self.session_id)
        self.callback_hub.create(self.session_id)

        self._manager_client: ManagerClient = await self.process_hub.create_session(
            self.session_id,
            pre_arena_callback=self._pre_arena_callback,
            in_arena_callback=self._in_arena_callback,
            post_arena_callback=self._post_arena_callback,
            pre_panel_callback=self._pre_panel_callback,
            in_panel_callback=self._in_panel_callback,
            post_panel_callback=self._post_panel_callback,
        )

        self._load_config()
        await self._refresh_config()

    async def set_config_data(self, config_data: dict[str, Any]) -> None:
        self._config_data: dict[str, Any] = config_data
        await self.update_config()

    async def update_config(self) -> bool:
        if dirty := await self._update_config():
            await self._load_motion(None)

        return dirty

    async def select_debate(self, value: str | None) -> None:
        self._cur_motion = value
        await self._load_motion(value)
        self._init_debate()

    async def reset_debate(self) -> None:
        if self.is_dirty:
            self._init_debate()

    async def start_debate(self) -> DebateResult | None:
        result: DebateResult | None = None

        with self._bg_task(is_debate=True):
            self._record_dirty = True
            self._panel_done_countdown = self.config_buffer.get_verdict_count(self.session_id)

            try:
                async with TaskGroup() as tg:
                    self._running_debate = tg.create_task(self._manager_client.manager_run())
                    tg.create_task(self._all_arena_callback_done.wait())
                    tg.create_task(self._all_panel_callback_done.wait())

                if self._running_debate is not None:
                    result = self._running_debate.result()
            except CancelledError:
                pass

            self._running_debate = None
            self._all_arena_callback_done.clear()
            self._all_panel_callback_done.clear()

        return result

    async def stop_debate(self) -> None:
        if self._running_debate is not None:
            self._running_debate.cancel()

            try:
                await self._running_debate
            except CancelledError:
                pass

            self._running_debate = None
            self._all_arena_callback_done.set()
            self._all_panel_callback_done.set()

    async def save_record(self) -> Path:
        assert self._cur_motion is not None

        return self._dump_record(
            f"{self._cur_motion}_{datetime.strftime(datetime.now(), '%Y%m%d%H%M%S%f')}"
        )

    async def close(self) -> None:
        await self._manager_client.close()

    def _load_config(self) -> None:
        with self._bg_task():
            self._config_data = self.config_buffer.get_config_data(self.session_id)

    async def _refresh_config(self) -> None:
        with self._bg_task():
            await self.config_buffer.configure(self.session_id)

    async def _update_config(self) -> bool:
        with self._bg_task():
            return await self.config_buffer.configure(self.session_id, config_data=self.config_data)

    async def _load_motion(self, motion_id: str | None, /) -> None:
        with self._bg_task():
            if motion_id is not None:
                await self.process_hub.arena_load(
                    self.session_id, speeches=self.resource_hub.speech.load(motion_id)
                )

                self._cur_info = self.resource_hub.motion.load(motion_id)
                await self._manager_client.manager_load(self._cur_info)
            else:
                self._cur_info = None

            self._can_start = motion_id is not None

    def _init_debate(self) -> None:
        with self._bg_task():
            self._running_debate = None
            self.recorder.reset()
            self.callback_hub.reset(self.session_id)

    def _dump_record(self, name: str, /) -> Path:
        with self._bg_task():
            return self.resource_hub.record.dump(name, self.recorder.records)

    async def _pre_arena_callback(self, debater_name: DebaterName, *args: Any) -> None:
        async def wrapped() -> None:
            await self.pre_arena_callback(*args, debater_name=debater_name)
            if debater_name == "":
                self._all_arena_callback_done.set()

        self.callback_hub.arena.put(
            self.session_id,
            wrapped(),
            stage=CallbackStage.PRE,
            key=debater_name,
            proceed=debater_name != "",
        )

    async def _in_arena_callback(self, debater_name: DebaterName, chunk: str | None) -> None:
        async def wrapped() -> None:
            await self.in_arena_callback(chunk, debater_name=debater_name)

        self.callback_hub.arena.put(
            self.session_id,
            wrapped(),
            stage=CallbackStage.IN,
            key=debater_name,
            proceed=chunk is None,
        )

    async def _post_arena_callback(self, debater_name: DebaterName, *args: Any) -> None:
        async def wrapped() -> None:
            await self.post_arena_callback(*args, debater_name=debater_name)
            self.recorder.add_speech(speech=args[0])

        self.callback_hub.arena.put(
            self.session_id, wrapped(), stage=CallbackStage.POST, key=debater_name
        )

    async def _pre_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any
    ) -> None:
        async def wrapped() -> None:
            await self.pre_panel_callback(*args, action=action, dimension_name=dimension_name)
            self.recorder.pre_add_comment(action=action, dimension_name=dimension_name)

        self.callback_hub.panel.put(
            self.session_id, wrapped(), stage=CallbackStage.PRE, key=(action, dimension_name)
        )

    async def _in_panel_callback(
        self,
        action: AllPanelActions,
        dimension_name: DimensionName,
        chat_chunk: tuple[str, str] | None,
    ) -> None:
        async def wrapped() -> None:
            await self.in_panel_callback(chat_chunk, action=action, dimension_name=dimension_name)

            self.recorder.add_comment(
                action=action, dimension_name=dimension_name, chat_chunk=chat_chunk
            )

        self.callback_hub.panel.put(
            self.session_id,
            wrapped(),
            stage=CallbackStage.IN,
            key=(action, dimension_name),
            proceed=chat_chunk is None,
        )

    async def _post_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any
    ) -> None:
        async def wrapped() -> None:
            await self.post_panel_callback(*args, action=action, dimension_name=dimension_name)
            self.recorder.post_add_comment(action=action, dimension_name=dimension_name)

            if action in (JudgeAction.JUDGE, PanelAction.SUMMARIZE):
                self._panel_done_countdown -= 1
                if self._panel_done_countdown == 0:
                    self._all_panel_callback_done.set()

        self.callback_hub.panel.put(
            self.session_id, wrapped(), stage=CallbackStage.POST, key=(action, dimension_name)
        )

    @contextmanager
    def _bg_task(self, *, is_debate: bool = False) -> Iterator[None]:
        self._num_bg_task += 1
        self._num_running_debate += is_debate

        try:
            yield
        finally:
            self._num_bg_task -= 1
            self._num_running_debate -= is_debate
