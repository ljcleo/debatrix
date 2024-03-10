from collections.abc import Iterable
from types import NoneType
from urllib.parse import quote

from ...api import APIClient
from ...core.common import (
    DimensionInfo,
    DimensionName,
    DimensionalVerdict,
    DebateInfo,
    Verdict,
    Speech,
)


class PanelInterfaceClient(APIClient):
    async def judge_create(
        self, dimension_name: DimensionName, /, *, dimension: DimensionInfo
    ) -> None:
        await self.query(quote(f"/judge/{dimension_name}/create"), dimension, output_type=NoneType)

    async def judge_reset(
        self, dimension_name: DimensionName, /, *, debate_info: DebateInfo
    ) -> None:
        await self.query(quote(f"/judge/{dimension_name}/reset"), debate_info, output_type=NoneType)

    async def judge_update(self, dimension_name: DimensionName, /, *, speech: Speech) -> None:
        await self.query(quote(f"/judge/{dimension_name}/update"), speech, output_type=NoneType)

    async def judge_judge(self, dimension_name: DimensionName, /) -> Verdict:
        result: Verdict | None = await self.query(
            quote(f"/judge/{dimension_name}/judge"), output_type=Verdict
        )

        if result is None:
            raise RuntimeError("judge judge result is null")

        return result

    async def panel_create(self) -> None:
        await self.query("/panel/create", output_type=NoneType)

    async def panel_reset(self, *, debate_info: DebateInfo) -> None:
        await self.query(quote("/panel/reset"), debate_info, output_type=NoneType)

    async def panel_summarize(self, *, verdicts: Iterable[DimensionalVerdict]) -> Verdict:
        result: Verdict | None = await self.query(
            "/panel/summarize", list(verdicts), output_type=Verdict
        )

        if result is None:
            raise RuntimeError("panel summarize result is null")

        return result
