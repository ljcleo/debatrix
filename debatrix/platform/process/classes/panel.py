from asyncio import CancelledError, run, sleep
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from socket import create_server, socket
from typing import cast

from uvicorn import Config, Server

from ....api import ServerInfo
from ....core.action import AllPanelActions
from ....core.common import DimensionName
from ....panel import (
    PanelInterfaceClient,
    PanelInterfaceConfig,
    PanelInterfaceServer,
    StreamingCallback,
)

CallbackMessage = tuple[str, AllPanelActions, DimensionName, tuple[str, str] | None]


class PanelInterfaceServerWithCallback(PanelInterfaceServer):
    @property
    def cb_queue(self) -> "Queue[CallbackMessage]":
        return self._cb_queue

    @cb_queue.setter
    def cb_queue(self, cb_queue: "Queue[CallbackMessage]") -> None:
        self._cb_queue = cb_queue

    async def callback(
        self,
        action: AllPanelActions,
        dimension_name: DimensionName,
        message: tuple[str, str] | None,
        /,
        *,
        session_id: str,
    ) -> None:
        self.cb_queue.put_nowait((session_id, action, dimension_name, message))


class PanelInterfaceProcess(Process):
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        super().__init__(daemon=True)

        self._server = PanelInterfaceServerWithCallback(debug=debug)

        self._uvicorn = Server(
            Config(app=self._server.app, log_level="info" if log_info else "warning")
        )

        self._socket: socket = create_server(("127.0.0.1", 0))
        self._server_info = ServerInfo(address=f"http://localhost:{self._socket.getsockname()[1]}")
        print("panel interface server at", self._server_info.address)

    @property
    def server_info(self) -> ServerInfo:
        return self._server_info

    @property
    def cb_queue(self) -> "Queue[CallbackMessage]":
        return self._server.cb_queue

    @cb_queue.setter
    def cb_queue(self, callback_queue: "Queue[CallbackMessage]") -> None:
        self._server.cb_queue = callback_queue

    def run(self) -> None:
        async def inner() -> None:
            try:
                await self._uvicorn.serve(sockets=[self._socket])
            finally:
                print("goodbye panel interface")
                await self._uvicorn.shutdown(sockets=[self._socket])
                await self._server.close()

        run(inner())


class PanelInterface:
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        self._process = PanelInterfaceProcess(debug=debug, log_info=log_info)
        self._sessions: dict[str, tuple[PanelInterfaceClient, StreamingCallback | None]] = {}

    @property
    def server_info(self) -> ServerInfo:
        return self._process.server_info

    def init_cb_queue(self, *, process_manager: SyncManager) -> None:
        self._process.cb_queue = cast("Queue[CallbackMessage]", process_manager.Queue())

    async def serve(self) -> None:
        self._process.start()

        try:
            while True:
                await sleep(0.01)

                try:
                    session_id: str
                    action: AllPanelActions
                    dimension_name: DimensionName
                    message: tuple[str, str] | None

                    session_id, action, dimension_name, message = (
                        self._process.cb_queue.get_nowait()
                    )
                except CancelledError:
                    raise
                except Exception:
                    continue

                if session_id in self._sessions:
                    callback: StreamingCallback | None = self._sessions[session_id][1]
                    if callback is not None:
                        await callback(action, dimension_name, message)
        finally:
            for client, *_ in self._sessions.values():
                await client.close()

    async def create_session(
        self, session_id: str, /, *, callback: StreamingCallback | None = None
    ) -> None:
        if session_id not in self._sessions:
            client = PanelInterfaceClient(session_id=session_id)
            client.set_server_info(self._process.server_info)
            self._sessions[session_id] = client, callback
            await client.create()

    async def set_model(self, session_id: str, /, *, server_info: ServerInfo) -> None:
        await self._sessions[session_id][0].set_model(server_info=server_info)

    async def configure(self, session_id: str, /, *, config: PanelInterfaceConfig) -> None:
        await self._sessions[session_id][0].configure(config=config)
