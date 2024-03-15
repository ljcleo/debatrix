from asyncio import CancelledError, Task, TaskGroup
from dataclasses import KW_ONLY, dataclass
from pathlib import Path
from socket import create_server, socket

from fastapi import FastAPI
from nicegui import ui
from uvicorn import Config, Server

from debatrix.platform import BasePlatform

from .session import UIBasedSession


@dataclass
class UIBasedPlatform(BasePlatform[UIBasedSession]):
    _: KW_ONLY
    ui_host: str = "0.0.0.0"
    ui_port: int = 58000

    def __post_init__(self, resource_root: Path) -> None:
        super().__post_init__(resource_root)
        ui.page("/")(self._register_ui)

        gui_app = FastAPI(debug=self.fast_api_debug)
        ui.run_with(gui_app, title="Debatrix Demo", favicon="♎", dark=None, storage_secret="COYG!")

        self._server = Server(
            Config(gui_app, log_level="info" if self.fast_api_log_info else "warning")
        )

        self._socket: socket = create_server((self.ui_host, self.ui_port), reuse_port=True)
        print("platform ui server at", f"http://{self.ui_host}:{self._socket.getsockname()[1]}")

    async def serve(self) -> None:
        async with TaskGroup() as tg:
            task: Task[None] = tg.create_task(super().serve())

            try:
                await self._server.serve(sockets=[self._socket])
            finally:
                print("goodbye gui")
                await self._server.shutdown(sockets=[self._socket])
                task.cancel()

                try:
                    await task
                except CancelledError:
                    pass

    def create_session(self) -> UIBasedSession:
        return UIBasedSession(
            resource_hub=self._resource_hub,
            process_hub=self._process_hub,
            recorder_hub=self._recorder_hub,
            config_buffer_hub=self._config_buffer_hub,
            arena_callback_arranger_manager=self._arena_callback_arranger_manager,
            panel_callback_arranger_manager=self._panel_callback_arranger_manager,
        )

    async def _register_ui(self) -> None:
        session: UIBasedSession = await self.assign()
        session.register_ui()
