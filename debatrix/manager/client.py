from types import NoneType
from urllib.parse import quote

from ..api import APIClient, ServerInfo
from ..core.common import DebateInfo, DebateResult
from .config import ManagerConfig


class ManagerClient(APIClient):
    def __init__(self, *, session_id: str, timeout: int = 30) -> None:
        super().__init__(timeout=timeout)
        self._session_id = session_id

    async def create(self) -> None:
        await self.query(self._quote("/create"), output_type=NoneType)

    async def set_arena(self, *, server_info: ServerInfo) -> None:
        await self.query(self._quote("/set_arena"), server_info, output_type=NoneType)

    async def set_panel(self, *, server_info: ServerInfo) -> None:
        await self.query(self._quote("/set_panel"), server_info, output_type=NoneType)

    async def configure(self, *, config: ManagerConfig) -> None:
        await self.query(self._quote("/configure"), config, output_type=NoneType)

    async def manager_load(self, debate_info: DebateInfo, /) -> None:
        await self.query(self._quote("/manager/load"), debate_info, output_type=NoneType)

    async def manager_run(self) -> DebateResult:
        result: DebateResult | None = await self.query(
            self._quote("/manager/run"), output_type=DebateResult
        )

        if result is None:
            raise RuntimeError("manager run result is null")

        return result

    def _quote(self, path: str) -> str:
        return quote(f"/{self._session_id}{path}")
