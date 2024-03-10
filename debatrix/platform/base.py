from asyncio import CancelledError, Event, Task, TaskGroup
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import KW_ONLY, InitVar, dataclass
from datetime import datetime
from multiprocessing import Manager
from pathlib import Path
from typing import Any

from ..core.action import AllPanelActions, JudgeAction, PanelAction
from ..core.common import DimensionName, DebateInfo, DebateResult, DebaterName, Speech
from ..manager import ManagerClient
from .callback import CallbackArrangerManager, CallbackStage
from .config_buffer import ConfigBufferHub
from .process import ProcessHub
from .record import DebateRecord
from .resource import ResourceHub


@dataclass
class Platform:
    resource_root: InitVar[Path]
    _: KW_ONLY
    debug: bool = False
    log_info: bool = True

    def __post_init__(self, resource_root: Path) -> None:
        self._resource_hub = ResourceHub(resource_root)

        self._process_hub = ProcessHub(
            debug=self.debug,
            log_info=self.log_info,
            pre_arena_callback=self._pre_arena_callback,
            in_arena_callback=self._in_arena_callback,
            post_arena_callback=self._post_arena_callback,
            pre_panel_callback=self._pre_panel_callback,
            in_panel_callback=self._in_panel_callback,
            post_panel_callback=self._post_panel_callback,
        )

        self._config_buffer_hub = ConfigBufferHub(self._resource_hub, self._process_hub)
        self._manager_client = ManagerClient()
        self._record = DebateRecord()

        self._cur_motion: str | None = None
        self._cur_info: DebateInfo | None = None

        self._can_start: bool = False
        self._num_bg_task: int = 0
        self._num_running_debate: int = 0

        self._running_debate: Task[DebateResult] | None = None
        self._panel_done_countdown: int = 0
        self._all_arena_callback_done = Event()
        self._all_panel_callback_done = Event()

        self._arena_callback_arrangers: CallbackArrangerManager[DebaterName] = (
            CallbackArrangerManager()
        )

        self._arena_activity_uuid: dict[DebaterName, str] = {}

        self._panel_callback_arrangers: CallbackArrangerManager[
            tuple[AllPanelActions, DimensionName]
        ] = CallbackArrangerManager()

        self._panel_activity_uuid: dict[tuple[AllPanelActions, DimensionName], str] = {}
        self._panel_message_incomplete: dict[tuple[AllPanelActions, DimensionName], bool] = {}

        self._load_model_config()
        self._load_arena_interface_config()
        self._load_panel_interface_config()
        self._load_dimensions()
        self._load_platform_config()

    @property
    def should_summarize(self) -> bool:
        return self._config_buffer_hub.platform.should_summarize

    @property
    def record_prompts(self) -> bool:
        return self._config_buffer_hub.platform.record_prompts

    @property
    def record_verdict_only(self) -> bool:
        return self._config_buffer_hub.platform.record_verdict_only

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
        return len(self._record.records) > 0 or self._running_debate is not None

    @property
    def motions(self) -> list[tuple[str, str]]:
        return self._resource_hub.motion.all_motions

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
    def dimensions_data(self) -> Any:
        return self._dimensions_data

    @property
    def platform_config_data(self) -> Any:
        return self._platform_config_data

    async def pre_arena_query_callback(self, *args: Any, debater_name: DebaterName) -> None:
        pass

    async def in_arena_query_callback(
        self, chunk: str | None, *, debater_name: DebaterName
    ) -> None:
        pass

    async def post_arena_query_callback(self, *args: Any, debater_name: DebaterName) -> None:
        speech: Speech | None = args[0]
        if speech is None:
            return

        if speech is not None and not self.record_verdict_only:
            self._record.update(
                self._arena_activity_uuid[debater_name], speech.debater_name, speech.content
            )

    async def pre_panel_action_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        pass

    async def in_panel_action_callback(
        self,
        chat_chunk: tuple[str, str] | None,
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
    ) -> None:
        if chat_chunk is not None:
            self._process_chat_list(action, dimension_name, chat_chunk)

    async def post_panel_action_callback(
        self, *args: Any, action: AllPanelActions, dimension_name: DimensionName
    ) -> None:
        pass

    async def serve(self) -> None:
        await self._process_hub.manager.initialize()

        self._process_hub.panel_interface.set_model(self._process_hub.model)

        self._process_hub.manager.set_interface(
            arena=self._process_hub.arena_interface, panel=self._process_hub.panel_interface
        )

        self._manager_client.set_server_info(self._process_hub.manager.server_info)

        with Manager() as process_manager:
            self._process_hub.manager.init_queues(process_manager=process_manager)
            self._process_hub.arena_interface.init_queues(process_manager=process_manager)
            self._process_hub.panel_interface.init_queues(process_manager=process_manager)
            self._process_hub.model.init_queues(process_manager=process_manager)

            try:
                async with TaskGroup() as tg:
                    tg.create_task(self._process_hub.manager.serve())
                    tg.create_task(self._process_hub.arena_interface.serve())
                    tg.create_task(self._process_hub.panel_interface.serve())
                    tg.create_task(self._process_hub.model.serve())
                    tg.create_task(self._arena_callback_arrangers.serve())
                    tg.create_task(self._panel_callback_arrangers.serve())
            finally:
                await self._manager_client.close()

    def refresh_config(self) -> None:
        self._refresh_model_config()
        self._refresh_arena_interface_config()
        self._refresh_panel_interface_config()
        self._refresh_dimensions()
        self._refresh_platform_config()

    async def update_config(self) -> bool:
        if dirty := any(
            [
                self._update_model_config(),
                self._update_arena_interface_config(),
                self._update_panel_interface_config(),
                self._update_dimensions(),
                self._update_platform_config(),
            ]
        ):
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

            self._panel_done_countdown = (
                1 if self.should_summarize else len(self._config_buffer_hub.manager.dimensions_name)
            )

            try:
                async with TaskGroup() as tg:
                    self._running_debate = tg.create_task(
                        self._manager_client.run(should_summarize=self.should_summarize)
                    )

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
            print("Send cancel signal to platform", flush=True)
            self._running_debate.cancel()

            from asyncio import sleep

            await sleep(0)

            try:
                await self._running_debate
            except CancelledError:
                pass

            print("Send cancel signal to manager", flush=True)
            self._process_hub.manager.cancel_tasks()
            print("Send cancel signal to arena", flush=True)
            self._process_hub.arena_interface.cancel_tasks()
            print("Send cancel signal to panel", flush=True)
            self._process_hub.panel_interface.cancel_tasks()
            print("Send cancel signal to model", flush=True)
            self._process_hub.model.cancel_tasks()

            print("set callback done", flush=True)
            self._all_arena_callback_done.set()
            self._all_panel_callback_done.set()

            self._running_debate = None

    async def save_record(self) -> str:
        assert self._cur_motion is not None
        name: str = f"{self._cur_motion}_{datetime.strftime(datetime.now(), '%Y%m%d%H%M%S%f')}"
        self._dump_record(name)
        return name

    def _load_model_config(self) -> None:
        with self._bg_task():
            self._model_config_data: Any = self._config_buffer_hub.model.model_config_data

    def _load_arena_interface_config(self) -> None:
        with self._bg_task():
            self._arena_interface_config_data: Any = (
                self._config_buffer_hub.arena_interface.interface_config_data
            )

    def _load_panel_interface_config(self) -> None:
        with self._bg_task():
            self._panel_interface_config_data: Any = (
                self._config_buffer_hub.panel_interface.interface_config_data
            )

    def _load_dimensions(self) -> None:
        with self._bg_task():
            self._dimensions_data: Any = self._config_buffer_hub.manager.dimensions_data

    def _load_platform_config(self) -> None:
        with self._bg_task():
            self._platform_config_data: Any = self._config_buffer_hub.platform.platform_config_data

    def _refresh_model_config(self) -> None:
        with self._bg_task():
            self._config_buffer_hub.model.update_model_config()

    def _refresh_arena_interface_config(self) -> None:
        with self._bg_task():
            self._config_buffer_hub.arena_interface.update_arena_interface_config()

    def _refresh_panel_interface_config(self) -> None:
        with self._bg_task():
            self._config_buffer_hub.panel_interface.update_panel_interface_config()

    def _refresh_dimensions(self) -> None:
        with self._bg_task():
            self._config_buffer_hub.manager.update_dimensions()

    def _refresh_platform_config(self) -> None:
        with self._bg_task():
            self._config_buffer_hub.platform.update_platform_config()

    def _update_model_config(self) -> bool:
        with self._bg_task():
            return self._config_buffer_hub.model.update_model_config(
                config_data=self.model_config_data
            )

    def _update_arena_interface_config(self) -> bool:
        with self._bg_task():
            return self._config_buffer_hub.arena_interface.update_arena_interface_config(
                config_data=self.arena_interface_config_data
            )

    def _update_panel_interface_config(self) -> bool:
        with self._bg_task():
            return self._config_buffer_hub.panel_interface.update_panel_interface_config(
                config_data=self.panel_interface_config_data
            )

    def _update_dimensions(self) -> bool:
        with self._bg_task():
            return self._config_buffer_hub.manager.update_dimensions(
                dimensions_data=self.dimensions_data
            )

    def _update_platform_config(self) -> bool:
        with self._bg_task():
            return self._config_buffer_hub.platform.update_platform_config(
                config_data=self.platform_config_data
            )

    async def _load_motion(self, motion_id: str | None, /) -> None:
        with self._bg_task():
            if motion_id is not None:
                self._process_hub.arena_interface.update_speeches(
                    self._resource_hub.speech.load(motion_id)
                )

                self._cur_info = self._resource_hub.motion.load(motion_id)
                await self._manager_client.update_info(self._cur_info)

                palette: tuple[str, ...] = ("primary", "secondary", "accent", "warning", "info")

                self._debaters_bg_color: dict[DebaterName, str] = {
                    debater_info.name: palette[index % len(palette)]
                    for index, debater_info in enumerate(self._cur_info.all_debaters_info)
                }
            else:
                self._cur_info = None

            self._can_start = motion_id is not None

    def _init_debate(self) -> None:
        with self._bg_task():
            self._record.reset()
            self._running_debate = None
            self._arena_callback_arrangers.reset()
            self._panel_callback_arrangers.reset()

    def _dump_record(self, name: str, /) -> None:
        with self._bg_task():
            self._resource_hub.record.dump(name, self._record.records)

    async def _pre_arena_callback(self, debater_name: DebaterName, *args: Any) -> None:
        async def wrapped() -> None:
            self._arena_activity_uuid[debater_name] = self._record.register()
            await self.pre_arena_query_callback(*args, debater_name=debater_name)

            if debater_name == "":
                self._all_arena_callback_done.set()

        self._arena_callback_arrangers.put(
            wrapped(), stage=CallbackStage.PRE, key=debater_name, proceed=debater_name != ""
        )

    async def _in_arena_callback(self, debater_name: DebaterName, chunk: str | None) -> None:
        async def wrapped() -> None:
            await self.in_arena_query_callback(chunk, debater_name=debater_name)

        self._arena_callback_arrangers.put(
            wrapped(), stage=CallbackStage.IN, key=debater_name, proceed=chunk is None
        )

    async def _post_arena_callback(self, debater_name: DebaterName, *args: Any) -> None:
        async def wrapped() -> None:
            await self.post_arena_query_callback(*args, debater_name=debater_name)
            self._arena_activity_uuid.pop(debater_name)

        self._arena_callback_arrangers.put(wrapped(), stage=CallbackStage.POST, key=debater_name)

    async def _pre_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any
    ) -> None:
        async def wrapped() -> None:
            self._panel_activity_uuid[action, dimension_name] = self._record.register()
            self._panel_message_incomplete[action, dimension_name] = False
            await self.pre_panel_action_callback(
                *args, action=action, dimension_name=dimension_name
            )

        self._panel_callback_arrangers.put(
            wrapped(), stage=CallbackStage.PRE, key=(action, dimension_name)
        )

    async def _in_panel_callback(
        self,
        action: AllPanelActions,
        dimension_name: DimensionName,
        chat_chunk: tuple[str, str] | None,
    ) -> None:
        async def wrapped() -> None:
            await self.in_panel_action_callback(
                chat_chunk, action=action, dimension_name=dimension_name
            )

        self._panel_callback_arrangers.put(
            wrapped(),
            stage=CallbackStage.IN,
            key=(action, dimension_name),
            proceed=chat_chunk is None,
        )

    async def _post_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any
    ) -> None:
        async def wrapped() -> None:
            await self.post_panel_action_callback(
                *args, action=action, dimension_name=dimension_name
            )
            self._panel_activity_uuid.pop((action, dimension_name))
            self._panel_message_incomplete.pop((action, dimension_name))

            self._panel_done_countdown -= (
                self.should_summarize and action == PanelAction.SUMMARIZE
            ) or (not self.should_summarize and action == JudgeAction.JUDGE)

            if self._panel_done_countdown == 0:
                self._all_panel_callback_done.set()

        self._panel_callback_arrangers.put(
            wrapped(), stage=CallbackStage.POST, key=(action, dimension_name)
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

    def _process_chat_list(
        self, action: AllPanelActions, dimension_name: DimensionName, chat_chunk: tuple[str, str]
    ) -> None:
        source: str
        content: str
        source, content = chat_chunk

        uuid: str = self._panel_activity_uuid[action, dimension_name]
        name: str = self._get_name(action, dimension_name)
        append: bool = source == "ai" and self._panel_message_incomplete[action, dimension_name]
        self._panel_message_incomplete[action, dimension_name] = source == "ai"

        if self.record_prompts or source in ("ai", "extra"):
            self._record.update(uuid, name, content, append=append)

    @staticmethod
    def _get_name(action: AllPanelActions, dimension_name: DimensionName) -> str:
        name: str = f"{action.value}_AI"
        if dimension_name != "":
            name = f"{dimension_name}_{name}"

        return name
