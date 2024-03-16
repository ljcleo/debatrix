from asyncio import TaskGroup, sleep
from collections.abc import Iterable
from multiprocessing import Queue
from multiprocessing.managers import SyncManager
from typing import Any, cast

from ...arena import ArenaInterfaceClient, ArenaInterfaceConfig, SpeechData
from ...arena import StreamingCallback as ArenaStreamingCallback
from ...arena import TaskCallback as ArenaTaskCallback
from ...manager import ManagerClient, ManagerConfig
from ...model import ModelClient, ModelConfig, ModelServer
from ...panel import PanelInterfaceClient, PanelInterfaceConfig
from ...panel import StreamingCallback as PanelStreamingCallback
from ...panel import TaskCallback as PanelTaskCallback
from .common import CallbackMessage, Part, SessionCallbacks, SessionClients, SessionData, Stage
from .process import SubProcess
from .server import (
    ArenaInterfaceServerWithCallback,
    ManagerServerWithCallback,
    PanelInterfaceServerWithCallback,
)


class ProcessHub:
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        self._model: SubProcess[ModelServer] = SubProcess(
            ModelServer, "model", debug=debug, log_info=log_info
        )

        self._arena: SubProcess[ArenaInterfaceServerWithCallback] = SubProcess(
            ArenaInterfaceServerWithCallback, "arena", debug=debug, log_info=log_info
        )

        self._panel: SubProcess[PanelInterfaceServerWithCallback] = SubProcess(
            PanelInterfaceServerWithCallback, "panel", debug=debug, log_info=log_info
        )

        self._manager: SubProcess[ManagerServerWithCallback] = SubProcess(
            ManagerServerWithCallback, "manager", debug=debug, log_info=log_info
        )

        self._sessions: dict[str, SessionData] = {}

    def setup(self, *, process_manager: SyncManager) -> None:
        self._queue: Queue["CallbackMessage"] = cast(
            "Queue[CallbackMessage]", process_manager.Queue()
        )

        self._arena.server.set_queue(self._queue)
        self._panel.server.set_queue(self._queue)
        self._manager.server.set_queue(self._queue)

    async def serve(self) -> None:
        try:
            self._model.start()
            self._arena.start()
            self._panel.start()
            self._manager.start()

            while True:
                await self._poll_callback()
        finally:
            async with TaskGroup() as tg:
                for session_data in self._sessions.values():
                    tg.create_task(session_data.clients.close())

    async def create_session(
        self,
        session_id: str,
        /,
        *,
        pre_arena_callback: ArenaTaskCallback | None = None,
        in_arena_callback: ArenaStreamingCallback | None = None,
        post_arena_callback: ArenaTaskCallback | None = None,
        pre_panel_callback: PanelTaskCallback | None = None,
        in_panel_callback: PanelStreamingCallback | None = None,
        post_panel_callback: PanelTaskCallback | None = None,
    ) -> ManagerClient:
        if session_id not in self._sessions:
            session_data = SessionData(
                clients=SessionClients(
                    model=ModelClient(session_id=session_id),
                    arena=ArenaInterfaceClient(session_id=session_id),
                    panel=PanelInterfaceClient(session_id=session_id),
                    manager=ManagerClient(session_id=session_id),
                ),
                callbacks=SessionCallbacks(
                    pre_arena=pre_arena_callback,
                    in_arena=in_arena_callback,
                    post_arena=post_arena_callback,
                    pre_panel=pre_panel_callback,
                    in_panel=in_panel_callback,
                    post_panel=post_panel_callback,
                ),
            )

            session_data.clients.model.set_server_info(self._model.server_info)
            session_data.clients.arena.set_server_info(self._arena.server_info)
            session_data.clients.panel.set_server_info(self._panel.server_info)
            session_data.clients.manager.set_server_info(self._manager.server_info)

            self._sessions[session_id] = session_data
            await session_data.clients.create()

            async with TaskGroup() as tg:
                tg.create_task(
                    session_data.clients.panel.set_model(server_info=self._model.server_info)
                )

                tg.create_task(
                    session_data.clients.manager.set_arena(server_info=self._arena.server_info)
                )

                tg.create_task(
                    session_data.clients.manager.set_panel(server_info=self._panel.server_info)
                )

        return self._sessions[session_id].clients.manager

    async def model_configure(self, session_id: str, /, *, config: ModelConfig) -> None:
        await self._sessions[session_id].clients.model.configure(config=config)

    async def arena_configure(self, session_id: str, /, *, config: ArenaInterfaceConfig) -> None:
        await self._sessions[session_id].clients.arena.configure(config=config)

    async def arena_load(self, session_id: str, /, *, speeches: Iterable[SpeechData]) -> None:
        await self._sessions[session_id].clients.arena.load(speeches=speeches)

    async def panel_configure(self, session_id: str, /, *, config: PanelInterfaceConfig) -> None:
        await self._sessions[session_id].clients.panel.configure(config=config)

    async def manager_configure(self, session_id: str, /, *, config: ManagerConfig) -> None:
        await self._sessions[session_id].clients.manager.configure(config=config)

    async def _poll_callback(self) -> None:
        await sleep(0)

        try:
            session_id: str
            part: Part
            stage: Stage
            args: tuple[Any, ...]
            session_id, part, stage, args = self._queue.get_nowait()
        except Exception:
            return

        if session_id in self._sessions:
            await self._sessions[session_id].callbacks.call(*args, part=part, stage=stage)
