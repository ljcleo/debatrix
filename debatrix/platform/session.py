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
from .callback import CallbackArrangerManager, CallbackStage
from .config_buffer import ConfigBufferHub
from .process import ProcessHub
from .record import Recorder, RecorderHub
from .resource import ResourceHub


@dataclass(kw_only=True)
class Session:
    resource_hub: ResourceHub
    process_hub: ProcessHub
    recorder_hub: RecorderHub
    config_buffer_hub: ConfigBufferHub
    arena_callback_arranger_manager: CallbackArrangerManager[DebaterName]
    panel_callback_arranger_manager: CallbackArrangerManager[tuple[AllPanelActions, DimensionName]]

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
    def model_config_data(self) -> Any:
        return self._model_config_data

    @property
    def arena_interface_config_data(self) -> Any:
        return self._arena_interface_config_data

    @property
    def panel_interface_config_data(self) -> Any:
        return self._panel_interface_config_data

    @property
    def manager_config_data(self) -> Any:
        return self._manager_config_data

    @property
    def recorder_config_data(self) -> Any:
        return self._recorder_config_data

    @property
    def session_state(self) -> dict[str, Any]:
        return dict(
            model=self.model_config_data,
            arena_interface=self.arena_interface_config_data,
            panel_interface=self.panel_interface_config_data,
            manager=self.manager_config_data,
            recorder=self.recorder_config_data,
        )

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

        async with TaskGroup() as tg:
            tg.create_task(
                self.process_hub.arena_interface.create_session(
                    self.session_id, callback=self._in_arena_callback
                )
            )

            tg.create_task(self.process_hub.model.create_session(self.session_id))

            tg.create_task(
                self.process_hub.panel_interface.create_session(
                    self.session_id, callback=self._in_panel_callback
                )
            )

            tg.create_task(
                self.process_hub.manager.create_session(
                    self.session_id,
                    pre_arena_callback=self._pre_arena_callback,
                    post_arena_callback=self._post_arena_callback,
                    pre_panel_callback=self._pre_panel_callback,
                    post_panel_callback=self._post_panel_callback,
                )
            )

        async with TaskGroup() as tg:
            tg.create_task(
                self.process_hub.panel_interface.set_model(
                    self.session_id, server_info=self.process_hub.model.server_info
                )
            )

            tg.create_task(
                self.process_hub.manager.set_arena(
                    self.session_id, server_info=self.process_hub.arena_interface.server_info
                )
            )

            tg.create_task(
                self.process_hub.manager.set_panel(
                    self.session_id, server_info=self.process_hub.panel_interface.server_info
                )
            )

        self._manager_client = ManagerClient(session_id=self.session_id)
        self._manager_client.set_server_info(self.process_hub.manager.server_info)

        self.arena_callback_arranger_manager.create(self.session_id)
        self.panel_callback_arranger_manager.create(self.session_id)

        self._load_model_config()
        self._load_arena_interface_config()
        self._load_panel_interface_config()
        self._load_manager_config()
        self._load_recorder_config()

        async with TaskGroup() as tg:
            tg.create_task(self._refresh_model_config())
            tg.create_task(self._refresh_arena_interface_config())
            tg.create_task(self._refresh_panel_interface_config())
            tg.create_task(self._refresh_manager_config())
            tg.create_task(self._refresh_recorder_config())

    async def set_session_state(self, state: dict[str, Any]) -> None:
        self._model_config_data = state["model"]
        self._arena_interface_config_data = state["arena_interface"]
        self._panel_interface_config_data = state["panel_interface"]
        self._manager_config_data = state["manager"]
        self._recorder_config_data = state["recorder"]
        await self.update_config()

    async def update_config(self) -> bool:
        async with TaskGroup() as tg:
            update_tasks: tuple[Task[bool], ...] = (
                tg.create_task(self._update_model_config()),
                tg.create_task(self._update_arena_interface_config()),
                tg.create_task(self._update_panel_interface_config()),
                tg.create_task(self._update_manager_config()),
                tg.create_task(self._update_recorder_config()),
            )

        if dirty := any(task.result() for task in update_tasks):
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

            self._panel_done_countdown = self.config_buffer_hub.manager.get_verdict_count(
                self.session_id
            )

            try:
                async with TaskGroup() as tg:
                    self._running_debate = tg.create_task(self._manager_client.manager_run())
                    tg.create_task(self._all_arena_callback_done.wait())
                    tg.create_task(self._all_panel_callback_done.wait())

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

    def _load_model_config(self) -> None:
        with self._bg_task():
            self._model_config_data: Any = self.config_buffer_hub.model.get_config_data(
                self.session_id
            )

    def _load_arena_interface_config(self) -> None:
        with self._bg_task():
            self._arena_interface_config_data: Any = (
                self.config_buffer_hub.arena_interface.get_config_data(self.session_id)
            )

    def _load_panel_interface_config(self) -> None:
        with self._bg_task():
            self._panel_interface_config_data: Any = (
                self.config_buffer_hub.panel_interface.get_config_data(self.session_id)
            )

    def _load_manager_config(self) -> None:
        with self._bg_task():
            self._manager_config_data: Any = self.config_buffer_hub.manager.get_config_data(
                self.session_id
            )

    def _load_recorder_config(self) -> None:
        with self._bg_task():
            self._recorder_config_data: Any = self.config_buffer_hub._recorder.get_config_data(
                self.session_id
            )

    async def _refresh_model_config(self) -> None:
        with self._bg_task():
            await self.config_buffer_hub.model.configure(self.session_id)

    async def _refresh_arena_interface_config(self) -> None:
        with self._bg_task():
            await self.config_buffer_hub.arena_interface.configure(self.session_id)

    async def _refresh_panel_interface_config(self) -> None:
        with self._bg_task():
            await self.config_buffer_hub.panel_interface.configure(self.session_id)

    async def _refresh_manager_config(self) -> None:
        with self._bg_task():
            await self.config_buffer_hub.manager.configure(self.session_id)

    async def _refresh_recorder_config(self) -> None:
        with self._bg_task():
            await self.config_buffer_hub.recorder.configure(self.session_id)

    async def _update_model_config(self) -> bool:
        with self._bg_task():
            return await self.config_buffer_hub.model.configure(
                self.session_id, config_data=self.model_config_data
            )

    async def _update_arena_interface_config(self) -> bool:
        with self._bg_task():
            return await self.config_buffer_hub.arena_interface.configure(
                self.session_id, config_data=self.arena_interface_config_data
            )

    async def _update_panel_interface_config(self) -> bool:
        with self._bg_task():
            return await self.config_buffer_hub.panel_interface.configure(
                self.session_id, config_data=self.panel_interface_config_data
            )

    async def _update_manager_config(self) -> bool:
        with self._bg_task():
            return await self.config_buffer_hub.manager.configure(
                self.session_id, config_data=self.manager_config_data
            )

    async def _update_recorder_config(self) -> bool:
        with self._bg_task():
            return await self.config_buffer_hub.recorder.configure(
                self.session_id, config_data=self.recorder_config_data
            )

    async def _load_motion(self, motion_id: str | None, /) -> None:
        with self._bg_task():
            if motion_id is not None:
                await self.process_hub.arena_interface.load(
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
            self.arena_callback_arranger_manager.reset(self.session_id)
            self.panel_callback_arranger_manager.reset(self.session_id)

    def _dump_record(self, name: str, /) -> Path:
        with self._bg_task():
            return self.resource_hub.record.dump(name, self.recorder.records)

    async def _pre_arena_callback(self, debater_name: DebaterName, *args: Any) -> None:
        async def wrapped() -> None:
            await self.pre_arena_callback(*args, debater_name=debater_name)
            if debater_name == "":
                self._all_arena_callback_done.set()

        self.arena_callback_arranger_manager.put(
            self.session_id,
            wrapped(),
            stage=CallbackStage.PRE,
            key=debater_name,
            proceed=debater_name != "",
        )

    async def _in_arena_callback(self, debater_name: DebaterName, chunk: str | None) -> None:
        async def wrapped() -> None:
            await self.in_arena_callback(chunk, debater_name=debater_name)

        self.arena_callback_arranger_manager.put(
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

        self.arena_callback_arranger_manager.put(
            self.session_id, wrapped(), stage=CallbackStage.POST, key=debater_name
        )

    async def _pre_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any
    ) -> None:
        async def wrapped() -> None:
            await self.pre_panel_callback(*args, action=action, dimension_name=dimension_name)
            self.recorder.pre_add_comment(action=action, dimension_name=dimension_name)

        self.panel_callback_arranger_manager.put(
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

        self.panel_callback_arranger_manager.put(
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

        self.panel_callback_arranger_manager.put(
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
