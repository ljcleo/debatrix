from typing import Any

from ...arena import ArenaInterfaceServer
from ...core.action import AllPanelActions
from ...core.common import DebaterName, DimensionName
from ...manager import ManagerServer
from ...panel import PanelInterfaceServer
from .common import HasCallbackQueueObject, Part, Stage


class ArenaInterfaceServerWithCallback(ArenaInterfaceServer, HasCallbackQueueObject):
    async def callback(
        self, debater_name: DebaterName, chunk: str | None, /, *, session_id: str
    ) -> None:
        self.send(debater_name, chunk, session_id=session_id, part=Part.ARENA, stage=Stage.IN)


class PanelInterfaceServerWithCallback(PanelInterfaceServer, HasCallbackQueueObject):
    async def callback(
        self,
        action: AllPanelActions,
        dimension_name: DimensionName,
        message: tuple[str, str] | None,
        /,
        *,
        session_id: str,
    ) -> None:
        self.send(
            action, dimension_name, message, session_id=session_id, part=Part.PANEL, stage=Stage.IN
        )


class ManagerServerWithCallback(ManagerServer, HasCallbackQueueObject):
    async def pre_arena_callback(
        self, debater_name: DebaterName, *args: Any, session_id: str
    ) -> None:
        self.send(debater_name, *args, session_id=session_id, part=Part.ARENA, stage=Stage.PRE)

    async def post_arena_callback(
        self, debater_name: DebaterName, *args: Any, session_id: str
    ) -> None:
        self.send(debater_name, *args, session_id=session_id, part=Part.ARENA, stage=Stage.POST)

    async def pre_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any, session_id: str
    ) -> None:
        self.send(
            action, dimension_name, *args, session_id=session_id, part=Part.PANEL, stage=Stage.PRE
        )

    async def post_panel_callback(
        self, action: AllPanelActions, dimension_name: DimensionName, *args: Any, session_id: str
    ) -> None:
        self.send(
            action, dimension_name, *args, session_id=session_id, part=Part.PANEL, stage=Stage.POST
        )
