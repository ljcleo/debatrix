from asyncio import CancelledError, run, sleep
from multiprocessing import Process, Queue
from multiprocessing.managers import SyncManager
from socket import create_server, socket
from typing import Any, Literal, cast

from uvicorn import Config, Server

from ....api import ServerInfo
from ....arena import TaskCallback as ArenaCallback
from ....core.action import AllPanelActions
from ....core.common import DebaterName, DimensionName
from ....manager import ManagerClient, ManagerConfig, ManagerServer
from ....panel import TaskCallback as PanelCallback

CallbackMessage = tuple[str, Literal["arena", "panel"], Literal["pre", "post"], tuple[Any, ...]]


class ManagerServerWithCallback(ManagerServer):
    @property
    def cb_queue(self) -> "Queue[CallbackMessage]":
        return self._cb_queue

    @cb_queue.setter
    def cb_queue(self, cb_queue: "Queue[CallbackMessage]") -> None:
        self._cb_queue = cb_queue

    async def pre_arena_callback(
        self, debater_name: DebaterName, *args: Any, session_id: str
    ) -> None:
        self.cb_queue.put_nowait((session_id, "arena", "pre", (debater_name, *args)))

    async def post_arena_callback(
        self, debater_name: DebaterName, *args: Any, session_id: str
    ) -> None:
        self.cb_queue.put_nowait((session_id, "arena", "post", (debater_name, *args)))

    async def pre_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any, session_id: str
    ) -> None:
        self.cb_queue.put_nowait((session_id, "panel", "pre", (action, dimension_name, *args)))

    async def post_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any, session_id: str
    ) -> None:
        self.cb_queue.put_nowait((session_id, "panel", "post", (action, dimension_name, *args)))


class ManagerProcess(Process):
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        super().__init__(daemon=True)

        self._server = ManagerServerWithCallback(debug=debug)

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
                print("goodbye manager")
                await self._uvicorn.shutdown(sockets=[self._socket])
                await self._server.close()

        run(inner())


class Manager:
    def __init__(self, *, debug: bool = False, log_info: bool = True):
        self._process = ManagerProcess(debug=debug, log_info=log_info)

        self._sessions: dict[
            str,
            tuple[
                ManagerClient,
                ArenaCallback | None,
                ArenaCallback | None,
                PanelCallback | None,
                PanelCallback | None,
            ],
        ] = {}

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
                    source: Literal["arena", "panel"]
                    stage: Literal["pre", "post"]
                    args: tuple[Any, ...]
                    session_id, source, stage, args = self._process.cb_queue.get_nowait()
                except CancelledError:
                    raise
                except Exception:
                    continue

                if session_id in self._sessions:
                    if source == "arena":
                        arena_callback: ArenaCallback | None

                        if stage == "pre":
                            arena_callback = self._sessions[session_id][1]
                        elif stage == "post":
                            arena_callback = self._sessions[session_id][2]
                        else:
                            raise RuntimeError(stage)

                        if arena_callback is not None:
                            await arena_callback(*args)
                    elif source == "panel":
                        panel_callback: PanelCallback | None

                        if stage == "pre":
                            panel_callback = self._sessions[session_id][3]
                        elif stage == "post":
                            panel_callback = self._sessions[session_id][4]
                        else:
                            raise RuntimeError(stage)

                        if panel_callback is not None:
                            await panel_callback(*args)
                    else:
                        raise RuntimeError(source)
        finally:
            for client, *_ in self._sessions.values():
                await client.close()

    async def create_session(
        self,
        session_id: str,
        /,
        *,
        pre_arena_callback: ArenaCallback | None = None,
        post_arena_callback: ArenaCallback | None = None,
        pre_panel_callback: PanelCallback | None = None,
        post_panel_callback: PanelCallback | None = None,
    ) -> None:
        if session_id not in self._sessions:
            client = ManagerClient(session_id=session_id)
            client.set_server_info(self._process.server_info)

            self._sessions[session_id] = (
                client,
                pre_arena_callback,
                post_arena_callback,
                pre_panel_callback,
                post_panel_callback,
            )

            await client.create()

    async def set_arena(self, session_id: str, /, *, server_info: ServerInfo) -> None:
        await self._sessions[session_id][0].set_arena(server_info=server_info)

    async def set_panel(self, session_id: str, /, *, server_info: ServerInfo) -> None:
        await self._sessions[session_id][0].set_panel(server_info=server_info)

    async def configure(self, session_id: str, /, *, config: ManagerConfig) -> None:
        await self._sessions[session_id][0].configure(config=config)
