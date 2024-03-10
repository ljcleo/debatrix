from types import NoneType
from urllib.parse import quote

from ...api import APIClient
from ...core.common import DebaterName, Speech


class ArenaInterfaceClient(APIClient):
    async def debater_reset(self, debater_name: DebaterName, /) -> None:
        await self.query(quote(f"/debater/{debater_name}/reset"), output_type=NoneType)

    async def debater_poll(self, debater_name: DebaterName, /) -> bool:
        result: bool | None = await self.query(
            quote(f"/debater/{debater_name}/poll"), output_type=bool
        )

        if result is None:
            raise RuntimeError("debater poll result is null")

        return result

    async def debater_query(self, debater_name: DebaterName, /) -> str:
        result: str | None = await self.query(
            quote(f"/debater/{debater_name}/query"), output_type=str
        )

        if result is None:
            raise RuntimeError("debater query result is null")

        return result

    async def debater_update(self, debater_name: DebaterName, /, *, speech: Speech) -> None:
        await self.query(quote(f"/debater/{debater_name}/update"), speech, output_type=NoneType)
