from asyncio import Task, TaskGroup, run, sleep
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from socket import create_server, socket
from typing import cast

from uvicorn import Config, Server

from ....api import ServerInfo
from ....core.action import AllPanelActions
from ....core.common import DimensionName
from ....panel import PanelInterfaceConfig, PanelInterfaceServer, StreamingCallback
from .model import Model

CallbackMessage = tuple[AllPanelActions, DimensionName, tuple[str, str] | None]


class PanelInterfaceProcess(Process):
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        super().__init__(daemon=True)

        self._server = PanelInterfaceServer(debug=debug, callback=self._callback)

        self._uvicorn = Server(
            Config(
                app=self._server.app,
                log_level="info" if log_info else "warning",
            )
        )

        self._socket: socket = create_server(("127.0.0.1", 0))
        self._server_info = ServerInfo(address=f"http://localhost:{self._socket.getsockname()[1]}")
        print("panel interface server at", self._server_info.address)

    @property
    def server_info(self) -> ServerInfo:
        return self._server_info

    @property
    def config_queue(self) -> "Queue[PanelInterfaceConfig]":
        return self._config_queue

    @property
    def cancellation_queue(self) -> "Queue[None]":
        return self._cancellation_queue

    @property
    def callback_queue(self) -> "Queue[CallbackMessage]":
        return self._callback_queue

    @config_queue.setter
    def config_queue(self, config_queue: "Queue[PanelInterfaceConfig]") -> None:
        self._config_queue = config_queue

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
                    print("goodbye panel interface")
                    await self._uvicorn.shutdown(sockets=[self._socket])
                    await self._server.close()
                    setup_task.cancel()

        run(inner())

    def set_model_server(self, *, server_info: ServerInfo) -> None:
        self._server.set_model_server(server_info=server_info)

    async def _callback(
        self,
        action: AllPanelActions,
        dimension_name: DimensionName,
        message: tuple[str, str] | None,
    ) -> None:
        self.callback_queue.put_nowait((action, dimension_name, message))

    async def _poll_setup(self) -> None:
        def poll_config() -> None:
            try:
                config: PanelInterfaceConfig = self.config_queue.get_nowait()
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


class PanelInterface:
    def __init__(
        self,
        *,
        debug: bool = False,
        log_info: bool = True,
        callback: StreamingCallback | None = None,
    ) -> None:
        self._callback = callback
        self._process = PanelInterfaceProcess(debug=debug, log_info=log_info)

    @property
    def server_info(self) -> ServerInfo:
        return self._process.server_info

    def set_model(self, model: Model, /) -> None:
        self._process.set_model_server(server_info=model.server_info)

    def init_queues(self, *, process_manager: SyncManager) -> None:
        self._process.config_queue = cast("Queue[PanelInterfaceConfig]", process_manager.Queue())
        self._process.cancellation_queue = cast("Queue[None]", process_manager.Queue())
        self._process.callback_queue = cast("Queue[CallbackMessage]", process_manager.Queue())

    async def serve(self) -> None:
        self._process.start()

        while True:
            await sleep(0.01)

            try:
                action: AllPanelActions
                dimension_name: DimensionName
                message: tuple[str, str] | None
                action, dimension_name, message = self._process.callback_queue.get_nowait()
            except Exception:
                continue

            if self._callback is not None:
                await self._callback(action, dimension_name, message)

    def update_panel_interface_config(self, config: PanelInterfaceConfig, /) -> None:
        self._process.config_queue.put_nowait(config)

    def cancel_tasks(self) -> None:
        self._process.cancellation_queue.put_nowait(None)
