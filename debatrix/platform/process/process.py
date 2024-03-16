from asyncio import run
from multiprocessing import Process
from socket import create_server, socket
from typing import Generic, TypeVar

from uvicorn import Config, Server

from ...api import APIServer, ServerInfo

T = TypeVar("T", bound=APIServer)


class SubProcess(Process, Generic[T]):
    def __init__(
        self, server_type: type[T], hint: str, /, *, debug: bool = False, log_info: bool = True
    ) -> None:
        super().__init__(daemon=True)

        self._server: T = server_type(debug=debug)
        self._hint = hint

        self._uvicorn = Server(
            Config(app=self._server.app, log_level="info" if log_info else "warning")
        )

        self._socket: socket = create_server(("127.0.0.1", 0))
        self._server_info = ServerInfo(address=f"http://localhost:{self._socket.getsockname()[1]}")
        print(f"{self._hint} server at", self._server_info.address)

    @property
    def server_info(self) -> ServerInfo:
        return self._server_info

    @property
    def server(self) -> T:
        return self._server

    def run(self) -> None:
        async def inner() -> None:
            try:
                await self._uvicorn.serve(sockets=[self._socket])
            finally:
                print(f"goodbye {self._hint}")
                await self._uvicorn.shutdown(sockets=[self._socket])
                await self._server.close()

        run(inner())
