from asyncio import TaskGroup
from dataclasses import dataclass
from typing import Iterable

from ..api import ServerInfo
from ..arena import Arena
from ..arena import TaskCallback as ArenaCallback
from ..core.common import DimensionInfo
from ..core.component import BaseManager
from ..panel import Panel
from ..panel import TaskCallback as PanelCallback


@dataclass(kw_only=True)
class Manager(BaseManager[Arena, Panel]):
    pre_arena_callback: ArenaCallback | None = None
    post_arena_callback: ArenaCallback | None = None
    pre_panel_callback: PanelCallback | None = None
    post_panel_callback: PanelCallback | None = None

    @property
    def dimensions(self) -> tuple[DimensionInfo, ...]:
        return self.panel.dimensions

    async def create_arena(self) -> Arena:
        return Arena(
            parent=self,
            pre_query_callback=self.pre_arena_callback,
            post_query_callback=self.post_arena_callback,
        )

    async def create_panel(self) -> Panel:
        return Panel(
            parent=self,
            pre_callback=self.pre_panel_callback,
            post_callback=self.post_panel_callback,
        )

    def set_arena_interface_server(self, *, server_info: ServerInfo) -> None:
        self.arena.set_interface_server(server_info=server_info)

    def set_panel_interface_server(self, *, server_info: ServerInfo) -> None:
        self.panel.set_interface_server(server_info=server_info)

    async def set_dimensions(self, dimensions: Iterable[DimensionInfo], /) -> None:
        await self.panel.set_dimensions(dimensions)

    async def close(self) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self.arena.close())
            tg.create_task(self.panel.close())
