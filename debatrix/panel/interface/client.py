from collections.abc import Iterable
from types import NoneType
from urllib.parse import quote

from ...api import APIClient, ServerInfo
from ...core.common import (
    DebateInfo,
    DimensionalVerdict,
    DimensionInfo,
    DimensionName,
    Speech,
    Verdict,
)
from .config import PanelInterfaceConfig


class PanelInterfaceClient(APIClient):
    def __init__(self, *, session_id: str, timeout: int = 30) -> None:
        super().__init__(timeout=timeout)
        self._session_id = session_id

    async def create(self) -> None:
        await self.query(self._quote("/create"), output_type=NoneType)

    async def set_model(self, *, server_info: ServerInfo) -> None:
        await self.query(self._quote("/set_model"), server_info, output_type=NoneType)

    async def configure(self, *, config: PanelInterfaceConfig) -> None:
        await self.query(self._quote("/configure"), config, output_type=NoneType)

    async def judge_create(
        self, dimension_name: DimensionName, /, *, dimension: DimensionInfo
    ) -> None:
        await self.query(
            self._quote(f"/judge/{dimension_name}/create"), dimension, output_type=NoneType
        )

    async def judge_reset(
        self, dimension_name: DimensionName, /, *, debate_info: DebateInfo
    ) -> None:
        await self.query(
            self._quote(f"/judge/{dimension_name}/reset"), debate_info, output_type=NoneType
        )

    async def judge_update(self, dimension_name: DimensionName, /, *, speech: Speech) -> None:
        await self.query(
            self._quote(f"/judge/{dimension_name}/update"), speech, output_type=NoneType
        )

    async def judge_judge(self, dimension_name: DimensionName, /) -> Verdict:
        result: Verdict | None = await self.query(
            self._quote(f"/judge/{dimension_name}/judge"), output_type=Verdict
        )

        if result is None:
            raise RuntimeError("judge judge result is null")

        return result

    async def panel_create(self) -> None:
        await self.query(self._quote("/panel/create"), output_type=NoneType)

    async def panel_reset(self, *, debate_info: DebateInfo) -> None:
        await self.query(self._quote("/panel/reset"), debate_info, output_type=NoneType)

    async def panel_summarize(self, *, verdicts: Iterable[DimensionalVerdict]) -> Verdict:
        result: Verdict | None = await self.query(
            self._quote("/panel/summarize"), list(verdicts), output_type=Verdict
        )

        if result is None:
            raise RuntimeError("panel summarize result is null")

        return result

    def _quote(self, path: str) -> str:
        return quote(f"/{self._session_id}{path}")
