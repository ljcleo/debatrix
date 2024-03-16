from asyncio import TaskGroup

from ...core.action import AllPanelActions
from ...core.common import DebaterName, DimensionName
from .manager import CallbackArrangerManager


class CallbackHub:
    def __init__(self) -> None:
        self._arena: CallbackArrangerManager[DebaterName] = CallbackArrangerManager()

        self._panel: CallbackArrangerManager[tuple[AllPanelActions, DimensionName]] = (
            CallbackArrangerManager()
        )

    @property
    def arena(self) -> CallbackArrangerManager[DebaterName]:
        return self._arena

    @property
    def panel(self) -> CallbackArrangerManager[tuple[AllPanelActions, DimensionName]]:
        return self._panel

    async def serve(self) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self._arena.serve())
            tg.create_task(self._panel.serve())

    def create(self, session_id: str, /) -> None:
        self._arena.create(session_id)
        self._panel.create(session_id)

    def reset(self, session_id: str, /) -> None:
        self._arena.reset(session_id)
        self._panel.reset(session_id)
