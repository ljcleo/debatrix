from types import NoneType

from ..api import APIClient
from ..core.common import DebateInfo, DebateResult


class ManagerClient(APIClient):
    async def update_info(self, debate_info: DebateInfo, /) -> None:
        await self.query("/manager/update_info", debate_info, output_type=NoneType)

    async def run(self, *, should_summarize: bool) -> DebateResult:
        result: DebateResult | None = await self.query(
            "/manager/run", should_summarize, output_type=DebateResult
        )

        if result is None:
            raise RuntimeError("manager run result is null")

        return result
