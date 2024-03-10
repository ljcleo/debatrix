from asyncio import Task, TaskGroup, run, sleep
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from socket import create_server, socket
from typing import Any, Literal, cast

from uvicorn import Config, Server

from ....api import ServerInfo
from ....arena import TaskCallback as ArenaCallback
from ....core.action import AllPanelActions
from ....core.common import DebaterName, DimensionInfo, DimensionName
from ....manager import ManagerServer
from ....panel import TaskCallback as PanelCallback
from .arena import ArenaInterface
from .panel import PanelInterface

Dimensions = tuple[DimensionInfo, ...]
CallbackMessage = tuple[Literal["arena", "panel"], Literal["pre", "post"], tuple[Any, ...]]


class ManagerProcess(Process):
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        super().__init__(daemon=True)

        self._server = ManagerServer(
            debug=debug,
            pre_arena_callback=self._pre_arena_callback,
            post_arena_callback=self._post_arena_callback,
            pre_panel_callback=self._pre_panel_callback,
            post_panel_callback=self._post_panel_callback,
        )

        self._uvicorn = Server(
            Config(app=self._server.app, log_level="info" if log_info else "warning")
        )

        self._socket: socket = create_server(("127.0.0.1", 0))
        self._server_info = ServerInfo(address=f"http://localhost:{self._socket.getsockname()[1]}")
        print("manager server at", self._server_info.address)

    @property
    def server_info(self) -> ServerInfo:
        return self._server_info

    @property
    def dimensions_queue(self) -> "Queue[Dimensions]":
        return self._dimensions_queue

    @property
    def cancellation_queue(self) -> "Queue[None]":
        return self._cancellation_queue

    @property
    def callback_queue(self) -> "Queue[CallbackMessage]":
        return self._callback_queue

    @dimensions_queue.setter
    def dimensions_queue(self, dimensions_queue: "Queue[Dimensions]") -> None:
        self._dimensions_queue = dimensions_queue

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
                    print("goodbye manager")
                    await self._uvicorn.shutdown(sockets=[self._socket])
                    await self._server.close()
                    setup_task.cancel()

        run(inner())

    async def initialize(self) -> None:
        await self._server.initialize()

    def set_arena_interface_server(self, *, server_info: ServerInfo) -> None:
        self._server.set_arena_interface_server(server_info=server_info)

    def set_panel_interface_server(self, *, server_info: ServerInfo) -> None:
        self._server.set_panel_interface_server(server_info=server_info)

    async def _pre_arena_callback(self, debater_name: DebaterName, *args: Any) -> None:
        self.callback_queue.put_nowait(("arena", "pre", (debater_name, *args)))

    async def _post_arena_callback(self, debater_name: DebaterName, *args: Any) -> None:
        self.callback_queue.put_nowait(("arena", "post", (debater_name, *args)))

    async def _pre_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any
    ) -> None:
        self.callback_queue.put_nowait(("panel", "pre", (action, dimension_name, *args)))

    async def _post_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any
    ) -> None:
        self.callback_queue.put_nowait(("panel", "post", (action, dimension_name, *args)))

    async def _poll_setup(self) -> None:
        async def poll_dimensions() -> None:
            try:
                dimensions: tuple[DimensionInfo, ...] = self.dimensions_queue.get_nowait()
            except Exception:
                return

            await self._server.set_dimensions(dimensions)

        async def poll_cancellation() -> None:
            try:
                self.cancellation_queue.get_nowait()
            except Exception:
                return

            await self._server.cancel_tasks()

        while True:
            await sleep(0.01)
            await poll_dimensions()
            await poll_cancellation()


class Manager:
    def __init__(
        self,
        *,
        debug: bool = False,
        log_info: bool = True,
        pre_arena_callback: ArenaCallback | None = None,
        post_arena_callback: ArenaCallback | None = None,
        pre_panel_callback: PanelCallback | None = None,
        post_panel_callback: PanelCallback | None = None,
    ):
        self._arena_callbacks: dict[Literal["pre", "post"], ArenaCallback | None] = dict(
            pre=pre_arena_callback, post=post_arena_callback
        )

        self._panel_callbacks: dict[Literal["pre", "post"], PanelCallback | None] = dict(
            pre=pre_panel_callback, post=post_panel_callback
        )

        self._process = ManagerProcess(debug=debug, log_info=log_info)

    @property
    def server_info(self) -> ServerInfo:
        return self._process.server_info

    async def initialize(self) -> None:
        await self._process.initialize()

    def set_interface(self, *, arena: ArenaInterface, panel: PanelInterface) -> None:
        self._process.set_arena_interface_server(server_info=arena.server_info)
        self._process.set_panel_interface_server(server_info=panel.server_info)

    def init_queues(self, *, process_manager: SyncManager) -> None:
        self._process.dimensions_queue = cast("Queue[Dimensions]", process_manager.Queue())
        self._process.cancellation_queue = cast("Queue[None]", process_manager.Queue())
        self._process.callback_queue = cast("Queue[CallbackMessage]", process_manager.Queue())

    async def serve(self) -> None:
        self._process.start()

        while True:
            await sleep(0.01)

            try:
                source: Literal["arena", "panel"]
                stage: Literal["pre", "post"]
                args: tuple[Any, ...]
                source, stage, args = self._process.callback_queue.get_nowait()
            except Exception:
                continue

            if source == "arena":
                arena_callback: ArenaCallback | None = self._arena_callbacks[stage]
                if arena_callback is not None:
                    await arena_callback(*args)
            elif source == "panel":
                panel_callback: PanelCallback | None = self._panel_callbacks[stage]
                if panel_callback is not None:
                    await panel_callback(*args)
            else:
                raise RuntimeError(source)

    def update_dimensions(self, dimensions: Dimensions, /) -> None:
        self._process.dimensions_queue.put_nowait(dimensions)

    def cancel_tasks(self) -> None:
        self._process.cancellation_queue.put_nowait(None)
