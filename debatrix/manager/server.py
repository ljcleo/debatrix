from collections.abc import Iterable
from typing import Annotated

from fastapi import Body

from ..api import APIServer, ServerInfo
from ..arena import TaskCallback as ArenaCallback
from ..core.common import DebateInfo, DebateResult, DimensionInfo
from ..panel import TaskCallback as PanelCallback
from .base import Manager


class ManagerServer(APIServer):
    def __init__(
        self,
        *,
        debug: bool = False,
        pre_arena_callback: ArenaCallback | None = None,
        post_arena_callback: ArenaCallback | None = None,
        pre_panel_callback: PanelCallback | None = None,
        post_panel_callback: PanelCallback | None = None,
    ) -> None:
        super().__init__(debug=debug)

        self._manager = Manager(
            pre_arena_callback=pre_arena_callback,
            post_arena_callback=post_arena_callback,
            pre_panel_callback=pre_panel_callback,
            post_panel_callback=post_panel_callback,
        )

        self.assign("/manager/update_info", self.update_info)
        self.assign("/manager/run", self.run)

    @property
    def dimensions(self) -> tuple[DimensionInfo, ...]:
        return self._manager.dimensions

    async def initialize(self) -> None:
        await self._manager.initialize()

    def set_arena_interface_server(self, *, server_info: ServerInfo) -> None:
        self._manager.set_arena_interface_server(server_info=server_info)

    def set_panel_interface_server(self, *, server_info: ServerInfo) -> None:
        self._manager.set_panel_interface_server(server_info=server_info)

    async def set_dimensions(self, dimensions: Iterable[DimensionInfo], /) -> None:
        await self._manager.set_dimensions(dimensions)

    async def close(self) -> None:
        await self._manager.close()

    async def update_info(self, debate_info: DebateInfo) -> None:
        await self._manager.update_info(debate_info)

    async def run(self, should_summarize: Annotated[bool, Body()]) -> DebateResult:
        return await self._manager.run(should_summarize=should_summarize)
