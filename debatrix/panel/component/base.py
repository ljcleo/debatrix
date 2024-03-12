from typing import Any

from ...core.action import AllPanelActions
from ...core.common import DimensionName
from ...core.component import DebateObject
from ..interface import PanelInterfaceClient
from .common import Stage


class HasInterfaceObject(DebateObject):
    @property
    def interface(self) -> PanelInterfaceClient:
        if isinstance(self.parent, HasInterfaceObject):
            return self.parent.interface
        else:
            raise NotImplementedError()

    async def callback(
        self, *args: Any, action: AllPanelActions, stage: Stage, dimension_name: DimensionName
    ) -> None:
        if isinstance(self.parent, HasInterfaceObject):
            await self.parent.callback(
                *args, action=action, stage=stage, dimension_name=dimension_name
            )
        else:
            raise NotImplementedError()
