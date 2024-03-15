from abc import abstractmethod
from asyncio import TaskGroup
from dataclasses import KW_ONLY, InitVar, dataclass
from multiprocessing import Manager
from pathlib import Path
from typing import Generic, TypeVar

from ..core.action import AllPanelActions
from ..core.common import DebaterName, DimensionName
from .callback import CallbackArrangerManager
from .config_buffer import ConfigBufferHub
from .process import ProcessHub
from .record import RecorderHub
from .resource import ResourceHub
from .session import Session

T = TypeVar("T", bound=Session)


@dataclass
class BasePlatform(Generic[T]):
    resource_root: InitVar[Path]
    _: KW_ONLY
    fast_api_debug: bool = False
    fast_api_log_info: bool = True
    dump_config_after_update: bool = False

    def __post_init__(self, resource_root: Path) -> None:
        self._resource_hub = ResourceHub(resource_root)
        self._process_hub = ProcessHub(debug=self.fast_api_debug, log_info=self.fast_api_log_info)
        self._recorder_hub = RecorderHub()

        self._config_buffer_hub = ConfigBufferHub(
            self._resource_hub,
            self._process_hub,
            self._recorder_hub,
            dump_after_update=self.dump_config_after_update,
        )

        self._arena_callback_arranger_manager: CallbackArrangerManager[DebaterName] = (
            CallbackArrangerManager()
        )

        self._panel_callback_arranger_manager: CallbackArrangerManager[
            tuple[AllPanelActions, DimensionName]
        ] = CallbackArrangerManager()

        self._sessions: dict[str, T] = {}

    async def serve(self) -> None:
        with Manager() as process_manager:
            self._process_hub.manager.init_cb_queue(process_manager=process_manager)
            self._process_hub.arena_interface.init_cb_queue(process_manager=process_manager)
            self._process_hub.panel_interface.init_cb_queue(process_manager=process_manager)

            try:
                async with TaskGroup() as tg:
                    tg.create_task(self._process_hub.manager.serve())
                    tg.create_task(self._process_hub.arena_interface.serve())
                    tg.create_task(self._process_hub.panel_interface.serve())
                    tg.create_task(self._process_hub.model.serve())
                    tg.create_task(self._arena_callback_arranger_manager.serve())
                    tg.create_task(self._panel_callback_arranger_manager.serve())
            finally:
                async with TaskGroup() as tg:
                    for session in self._sessions.values():
                        tg.create_task(session.close())

    async def assign(self) -> T:
        session: T = self.create_session()
        await session.setup()
        self._sessions[session.session_id] = session
        return session

    @abstractmethod
    def create_session(self) -> T:
        raise NotImplementedError()


@dataclass
class Platform(BasePlatform[Session]):
    def create_session(self) -> Session:
        return Session(
            resource_hub=self._resource_hub,
            process_hub=self._process_hub,
            recorder_hub=self._recorder_hub,
            config_buffer_hub=self._config_buffer_hub,
            arena_callback_arranger_manager=self._arena_callback_arranger_manager,
            panel_callback_arranger_manager=self._panel_callback_arranger_manager,
        )
