from asyncio import Task, TaskGroup, run, sleep
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from socket import create_server, socket
from typing import cast

from uvicorn import Config, Server

from ....api import ServerInfo
from ....arena import ArenaInterfaceConfig, ArenaInterfaceServer, SpeechData, StreamingCallback
from ....core.common import DebaterName

Speeches = list[SpeechData]
CallbackMessage = tuple[DebaterName, str | None]


class ArenaInterfaceProcess(Process):
    def __init__(self, /, *, debug: bool = False, log_info: bool = True) -> None:
        super().__init__(daemon=True)

        self._server = ArenaInterfaceServer(debug=debug, callback=self._callback)

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
    def config_queue(self) -> "Queue[ArenaInterfaceConfig]":
        return self._config_queue

    @property
    def speeches_queue(self) -> "Queue[Speeches]":
        return self._speeches_queue

    @property
    def cancellation_queue(self) -> "Queue[None]":
        return self._cancellation_queue

    @property
    def callback_queue(self) -> "Queue[CallbackMessage]":
        return self._callback_queue

    @config_queue.setter
    def config_queue(self, config_queue: "Queue[ArenaInterfaceConfig]") -> None:
        self._config_queue = config_queue

    @speeches_queue.setter
    def speeches_queue(self, speeches_queue: "Queue[Speeches]") -> None:
        self._speeches_queue = speeches_queue

    @cancellation_queue.setter
    def cancellation_queue(self, cancellation_queue: "Queue[None]") -> None:
        self._cancellation_queue = cancellation_queue

    @callback_queue.setter
    def callback_queue(self, callback_queue: "Queue[CallbackMessage]") -> None:
        self._callback_queue = callback_queue

    def run(self) -> None:
        async def inner() -> None:
            async with TaskGroup() as tg:
                setup_task: Task[None] = tg.create_task(self._poll_setup())

                try:
                    await self._uvicorn.serve(sockets=[self._socket])
                finally:
                    print("goodbye arena interface")
                    await self._uvicorn.shutdown(sockets=[self._socket])
                    await self._server.close()
                    setup_task.cancel()

        run(inner())

    async def _callback(self, debater_name: DebaterName, chunk: str | None) -> None:
        self.callback_queue.put_nowait((debater_name, chunk))

    async def _poll_setup(self) -> None:
        def poll_config() -> None:
            try:
                config: ArenaInterfaceConfig = self.config_queue.get_nowait()
            except Exception:
                return

            self._server.config = config

        def poll_speeches() -> None:
            try:
                speeches: list[SpeechData] = self.speeches_queue.get_nowait()
            except Exception:
                return

            if speeches is not None:
                self._server.set_speeches(speeches)

        async def poll_cancellation() -> None:
            try:
                self.cancellation_queue.get_nowait()
            except Exception:
                return

            await self._server.cancel_tasks()

        while True:
            await sleep(0.01)
            poll_config()
            poll_speeches()
            await poll_cancellation()


class ArenaInterface:
    def __init__(
        self,
        *,
        debug: bool = False,
        log_info: bool = True,
        callback: StreamingCallback | None = None,
    ) -> None:
        self._callback = callback
        self._process = ArenaInterfaceProcess(debug=debug, log_info=log_info)

    @property
    def server_info(self) -> ServerInfo:
        return self._process.server_info

    def init_queues(self, *, process_manager: SyncManager) -> None:
        self._process.config_queue = cast("Queue[ArenaInterfaceConfig]", process_manager.Queue())
        self._process.speeches_queue = cast("Queue[Speeches]", process_manager.Queue())
        self._process.cancellation_queue = cast("Queue[None]", process_manager.Queue())
        self._process.callback_queue = cast("Queue[CallbackMessage]", process_manager.Queue())

    async def serve(self) -> None:
        self._process.start()

        while True:
            await sleep(0.01)

            try:
                debater_name: DebaterName
                chunk: str | None
                debater_name, chunk = self._process.callback_queue.get_nowait()
            except Exception:
                continue

            if self._callback is not None:
                await self._callback(debater_name, chunk)

    def update_arena_interface_config(self, config: ArenaInterfaceConfig, /) -> None:
        self._process.config_queue.put_nowait(config)

    def update_speeches(self, speeches: Speeches, /) -> None:
        self._process.speeches_queue.put_nowait(speeches)

    def cancel_tasks(self) -> None:
        self._process.cancellation_queue.put_nowait(None)
