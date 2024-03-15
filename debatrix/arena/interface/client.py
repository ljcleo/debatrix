from collections.abc import Iterable
from types import NoneType
from urllib.parse import quote

from ...api import APIClient
from ...core.common import DebaterName, Speech
from .common import SpeechData
from .config import ArenaInterfaceConfig


class ArenaInterfaceClient(APIClient):
    def __init__(self, *, session_id: str, timeout: int = 30) -> None:
        super().__init__(timeout=timeout)
        self._session_id = session_id

    async def create(self) -> None:
        await self.query(self._quote("/create"), output_type=NoneType)

    async def configure(self, *, config: ArenaInterfaceConfig) -> None:
        await self.query(self._quote("/configure"), config, output_type=NoneType)

    async def load(self, *, speeches: Iterable[SpeechData]) -> None:
        await self.query(self._quote("/load"), list(speeches), output_type=NoneType)

    async def debater_reset(self, debater_name: DebaterName, /) -> None:
        await self.query(self._quote(f"/debater/{debater_name}/reset"), output_type=NoneType)

    async def debater_poll(self, debater_name: DebaterName, /) -> bool:
        result: bool | None = await self.query(
            self._quote(f"/debater/{debater_name}/poll"), output_type=bool
        )

        if result is None:
            raise RuntimeError("debater poll result is null")

        return result

    async def debater_query(self, debater_name: DebaterName, /) -> str:
        result: str | None = await self.query(
            self._quote(f"/debater/{debater_name}/query"), output_type=str
        )

        if result is None:
            raise RuntimeError("debater query result is null")

        return result

    async def debater_update(self, debater_name: DebaterName, /, *, speech: Speech) -> None:
        await self.query(
            self._quote(f"/debater/{debater_name}/update"), speech, output_type=NoneType
        )

    def _quote(self, path: str) -> str:
        return quote(f"/{self._session_id}{path}")
