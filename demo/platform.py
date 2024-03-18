from asyncio import CancelledError, Task, TaskGroup
from dataclasses import KW_ONLY, InitVar, dataclass
from pathlib import Path
from random import Random
from socket import create_server, socket

from fastapi import FastAPI
from nicegui import app, ui
from uvicorn import Config, Server

from debatrix.platform import BasePlatform

from .session import UIBasedSession


@dataclass
class UIBasedPlatform(BasePlatform[UIBasedSession]):
    _: KW_ONLY
    ui_host: str = "0.0.0.0"
    ui_port: int = 58000

    enable_intro: bool = False
    enable_full_config_ui: bool = False

    storage_secret: InitVar[str] = ""

    def __post_init__(self, resource_root: Path, storage_secret: str) -> None:
        super().__post_init__(resource_root)

        rng = Random(storage_secret)
        storage_secret = "".join([chr(rng.randint(33, 126)) for _ in range(16)])
        print("Using storage secret:", storage_secret)

        ui.page("/")(self._register_ui)
        app.on_startup(app.storage.clear)
        app.on_exception(lambda x: ui.notify(f"Internal Error: {repr(x)}", type="negative"))

        gui_app = FastAPI(debug=self.fast_api_debug)

        ui.run_with(
            gui_app, title="Debatrix Demo", favicon="♎", dark=None, storage_secret=storage_secret
        )

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
            config_buffer=self._config_buffer,
            callback_hub=self._callback_hub,
            enable_intro=self.enable_intro,
            enable_full_config_ui=self.enable_full_config_ui,
        )

    async def _register_ui(self) -> None:
        session: UIBasedSession = await self.assign()
        session.register_ui()
