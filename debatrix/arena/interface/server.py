from functools import partial

from ...api import APIServer
from ...core.common import DebaterName, Speech
from .base import ArenaInterface
from .common import SpeechData
from .config import ArenaInterfaceConfig


class ArenaInterfaceServer(APIServer):
    def __init__(self) -> None:
        super().__init__()
        self._interfaces: dict[str, ArenaInterface] = {}

    def init_app(self, /, *, debug: bool = False) -> None:
        super().init_app(debug=debug)

        self.assign("/{session_id}/create", self._create)
        self.assign("/{session_id}/configure", self._configure)
        self.assign("/{session_id}/load", self._load)

        self.assign("/{session_id}/debater/{debater_name}/reset", self._debater_reset)
        self.assign("/{session_id}/debater/{debater_name}/poll", self._debater_poll)
        self.assign("/{session_id}/debater/{debater_name}/query", self._debater_query)
        self.assign("/{session_id}/debater/{debater_name}/update", self._debater_update)

    async def callback(
        self, debater_name: DebaterName, chunk: str | None, /, *, session_id: str
    ) -> None:
        pass

    async def close(self) -> None:
        pass

    async def _create(self, session_id: str) -> None:
        self._interfaces[session_id] = ArenaInterface(
            callback=partial(self.callback, session_id=session_id)
        )

    async def _configure(self, session_id: str, config: ArenaInterfaceConfig) -> None:
        self._interfaces[session_id].config = config

    async def _load(self, session_id: str, speeches: list[SpeechData]) -> None:
        self._interfaces[session_id].set_speeches(speeches)

    async def _debater_reset(self, session_id: str, debater_name: DebaterName) -> None:
        await self._interfaces[session_id].reset(debater_name)

    async def _debater_poll(self, session_id: str, debater_name: DebaterName) -> bool:
        return await self._interfaces[session_id].poll(debater_name)

    async def _debater_query(self, session_id: str, debater_name: DebaterName) -> str:
        return await self._interfaces[session_id].query(debater_name)

    async def _debater_update(
        self, session_id: str, debater_name: DebaterName, speech: Speech
    ) -> None:
        await self._interfaces[session_id].update(debater_name, speech=speech)
