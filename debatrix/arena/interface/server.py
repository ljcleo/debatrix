from collections.abc import Iterable

from ...api import APIServer
from ...core.common import DebaterName, Speech
from .base import ArenaInterface
from .common import SpeechData, StreamingCallback
from .config import ArenaInterfaceConfig


class ArenaInterfaceServer(APIServer):
    def __init__(self, *, debug: bool = False, callback: StreamingCallback | None = None) -> None:
        super().__init__(debug=debug)

        self._interface = ArenaInterface(callback=callback)

        self.assign("/debater/{debater_name}/reset", self.reset)
        self.assign("/debater/{debater_name}/poll", self.poll)
        self.assign("/debater/{debater_name}/query", self.query)
        self.assign("/debater/{debater_name}/update", self.update)

    @property
    def config(self) -> ArenaInterfaceConfig:
        return self._interface.config

    @config.setter
    def config(self, config: ArenaInterfaceConfig) -> None:
        self._interface.config = config

    def set_speeches(self, speeches: Iterable[SpeechData], /) -> None:
        self._interface.set_speeches(speeches)

    async def close(self) -> None:
        pass

    async def reset(self, debater_name: DebaterName) -> None:
        await self._interface.reset(debater_name)

    async def poll(self, debater_name: DebaterName) -> bool:
        return await self._interface.poll(debater_name)

    async def query(self, debater_name: DebaterName) -> str:
        return await self._interface.query(debater_name)

    async def update(self, debater_name: DebaterName, speech: Speech) -> None:
        await self._interface.update(debater_name, speech)
