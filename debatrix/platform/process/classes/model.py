from asyncio import Task, TaskGroup, run, sleep
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from socket import create_server, socket
from typing import cast

from uvicorn import Config, Server

from ....api import ServerInfo
from ....model import ModelConfig, ModelServer


class ModelProcess(Process):
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        super().__init__(daemon=True)

        self._server = ModelServer(debug=debug)

        self._uvicorn = Server(
            Config(app=self._server.app, log_level="info" if log_info else "warning")
        )

        self._socket: socket = create_server(("127.0.0.1", 0))
        self._server_info = ServerInfo(address=f"http://localhost:{self._socket.getsockname()[1]}")
        print("panel model server at", self._server_info.address)

    @property
    def server_info(self) -> ServerInfo:
        return self._server_info

    @property
    def config_queue(self) -> "Queue[ModelConfig]":
        return self._config_queue

    @property
    def cancellation_queue(self) -> "Queue[None]":
        return self._cancellation_queue

    @config_queue.setter
    def config_queue(self, config_queue: "Queue[ModelConfig]") -> None:
        self._config_queue = config_queue

    @cancellation_queue.setter
    def cancellation_queue(self, cancellation_queue: "Queue[None]") -> None:
        self._cancellation_queue = cancellation_queue

    def run(self) -> None:
        async def inner() -> None:
            async with TaskGroup() as tg:
                setup_task: Task[None] = tg.create_task(self._poll_setup())

                try:
                    await self._uvicorn.serve(sockets=[self._socket])
                finally:
                    print("goodbye panel model")
                    await self._uvicorn.shutdown(sockets=[self._socket])
                    await self._server.close()
                    setup_task.cancel()

        run(inner())

    async def _poll_setup(self) -> None:
        def poll_config() -> None:
            try:
                config: ModelConfig = self.config_queue.get_nowait()
            except Exception:
                return

            self._server.config = config

        async def poll_cancellation() -> None:
            try:
                self.cancellation_queue.get_nowait()
            except Exception:
                return

            await self._server.cancel_tasks()

        while True:
            await sleep(0.01)
            poll_config()
            await poll_cancellation()


class Model:
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        self._process = ModelProcess(debug=debug, log_info=log_info)

    @property
    def server_info(self) -> ServerInfo:
        return self._process.server_info

    def init_queues(self, *, process_manager: SyncManager) -> None:
        self._process.config_queue = cast("Queue[ModelConfig]", process_manager.Queue())
        self._process.cancellation_queue = cast("Queue[None]", process_manager.Queue())

    async def serve(self) -> None:
        self._process.start()
        while True:
            await sleep(0.01)

    def update_model_config(self, config: ModelConfig, /) -> None:
        self._process.config_queue.put_nowait(config)

    def cancel_tasks(self) -> None:
        self._process.cancellation_queue.put_nowait(None)
