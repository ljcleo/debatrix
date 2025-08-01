from asyncio import TaskGroup
from functools import partial
from typing import Any

from ..api import APIServer, ServerInfo
from ..core.action import AllPanelActions
from ..core.common import DebateInfo, DebateResult, DebaterName, DimensionName
from .base import Manager
from .config import ManagerConfig


class ManagerServer(APIServer):
    def __init__(self) -> None:
        super().__init__()
        self._managers: dict[str, Manager] = {}

    def init_app(self, /, *, debug: bool = False) -> None:
        super().init_app(debug=debug)

        self.assign("/{session_id}/create", self._create)
        self.assign("/{session_id}/set_arena", self._set_arena)
        self.assign("/{session_id}/set_panel", self._set_panel)
        self.assign("/{session_id}/configure", self._configure)

        self.assign("/{session_id}/manager/load", self._manager_load)
        self.assign("/{session_id}/manager/run", self._manager_run)

    async def close(self) -> None:
        async with TaskGroup() as tg:
            for manager in self._managers.values():
                tg.create_task(manager.close())

    async def pre_arena_callback(
        self, debater_name: DebaterName, *args: Any, session_id: str
    ) -> None:
        pass

    async def post_arena_callback(
        self, debater_name: DebaterName, *args: Any, session_id: str
    ) -> None:
        pass

    async def pre_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any, session_id: str
    ) -> None:
        pass

    async def post_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any, session_id: str
    ) -> None:
        pass

    async def _create(self, session_id: str) -> None:
        self._managers[session_id] = Manager(
            session_id=session_id,
            pre_arena_callback=partial(self.pre_arena_callback, session_id=session_id),
            post_arena_callback=partial(self.post_arena_callback, session_id=session_id),
            pre_panel_callback=partial(self.pre_panel_callback, session_id=session_id),
            post_panel_callback=partial(self.post_panel_callback, session_id=session_id),
        )

        await self._managers[session_id].initialize()

    async def _set_arena(self, session_id: str, server_info: ServerInfo) -> None:
        self._managers[session_id].set_arena_interface_server(server_info=server_info)

    async def _set_panel(self, session_id: str, server_info: ServerInfo) -> None:
        self._managers[session_id].set_panel_interface_server(server_info=server_info)

    async def _configure(self, session_id: str, config: ManagerConfig) -> None:
        await self._managers[session_id].set_config(config)

    async def _manager_load(self, session_id: str, debate_info: DebateInfo) -> None:
        await self._managers[session_id].update_info(debate_info=debate_info)

    async def _manager_run(self, session_id: str) -> DebateResult:
        return await self._managers[session_id].run()
