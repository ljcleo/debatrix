from asyncio import CancelledError, run, sleep
from collections.abc import Iterable
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from socket import create_server, socket
from typing import cast

from uvicorn import Config, Server

from ....api import ServerInfo
from ....arena import (
    ArenaInterfaceClient,
    ArenaInterfaceConfig,
    ArenaInterfaceServer,
    SpeechData,
    StreamingCallback,
)
from ....core.common import DebaterName

CallbackMessage = tuple[str, DebaterName, str | None]


class ArenaInterfaceServerWithCallback(ArenaInterfaceServer):
    @property
    def cb_queue(self) -> "Queue[CallbackMessage]":
        return self._cb_queue

    @cb_queue.setter
    def cb_queue(self, cb_queue: "Queue[CallbackMessage]") -> None:
        self._cb_queue = cb_queue

    async def callback(
        self, debater_name: DebaterName, chunk: str | None, /, *, session_id: str
    ) -> None:
        self.cb_queue.put_nowait((session_id, debater_name, chunk))


class ArenaInterfaceProcess(Process):
    def __init__(self, /, *, debug: bool = False, log_info: bool = True) -> None:
        super().__init__(daemon=True)

        self._server = ArenaInterfaceServerWithCallback(debug=debug)

        self._uvicorn = Server(
            Config(app=self._server.app, log_level="info" if log_info else "warning")
        )

        self._socket: socket = create_server(("127.0.0.1", 0))
        self._server_info = ServerInfo(address=f"http://localhost:{self._socket.getsockname()[1]}")
        print("arena interface server at", self._server_info.address)

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
                print("goodbye arena interface")
                await self._uvicorn.shutdown(sockets=[self._socket])
                await self._server.close()

        run(inner())


class ArenaInterface:
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        self._process = ArenaInterfaceProcess(debug=debug, log_info=log_info)
        self._sessions: dict[str, tuple[ArenaInterfaceClient, StreamingCallback | None]] = {}

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
                    debater_name: DebaterName
                    chunk: str | None
                    session_id, debater_name, chunk = self._process.cb_queue.get_nowait()
                except CancelledError:
                    raise
                except Exception:
                    continue

                if session_id in self._sessions:
                    callback: StreamingCallback | None = self._sessions[session_id][1]
                    if callback is not None:
                        await callback(debater_name, chunk)
        finally:
            for client, *_ in self._sessions.values():
                await client.close()

    async def create_session(
        self, session_id: str, /, *, callback: StreamingCallback | None = None
    ) -> None:
        if session_id not in self._sessions:
            client = ArenaInterfaceClient(session_id=session_id)
            client.set_server_info(self._process.server_info)
            self._sessions[session_id] = client, callback
            await client.create()

    async def configure(self, session_id: str, /, *, config: ArenaInterfaceConfig) -> None:
        await self._sessions[session_id][0].configure(config=config)

    async def load(self, session_id: str, /, *, speeches: Iterable[SpeechData]) -> None:
        await self._sessions[session_id][0].load(speeches=speeches)
