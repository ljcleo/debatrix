from asyncio import run, sleep
from multiprocessing import Process
from socket import create_server, socket

from uvicorn import Config, Server

from ....api import ServerInfo
from ....model import ModelClient, ModelConfig, ModelServer


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

    def run(self) -> None:
        async def inner() -> None:
            try:
                await self._uvicorn.serve(sockets=[self._socket])
            finally:
                print("goodbye panel model")
                await self._uvicorn.shutdown(sockets=[self._socket])
                await self._server.close()

        run(inner())


class Model:
    def __init__(self, *, debug: bool = False, log_info: bool = True) -> None:
        self._process = ModelProcess(debug=debug, log_info=log_info)
        self._sessions: dict[str, ModelClient] = {}

    @property
    def server_info(self) -> ServerInfo:
        return self._process.server_info

    async def serve(self) -> None:
        try:
            self._process.start()
            while True:
                await sleep(0.01)
        finally:
            for client in self._sessions.values():
                await client.close()

    async def create_session(self, session_id: str, /) -> None:
        if session_id not in self._sessions:
            client = ModelClient(session_id=session_id)
            client.set_server_info(self._process.server_info)
            self._sessions[session_id] = client
            await client.create()

    async def configure(self, session_id: str, /, *, config: ModelConfig) -> None:
        await self._sessions[session_id].configure(config=config)
