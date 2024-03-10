from typing import Any

from ...core.common import DebaterName
from ...core.component import DebateObject
from ..interface import ArenaInterfaceClient
from .common import QueryStage


class HasInterfaceObject(DebateObject):
    @property
    def interface(self) -> ArenaInterfaceClient:
        if isinstance(self.parent, HasInterfaceObject):
            return self.parent.interface
        else:
            raise NotImplementedError()

    async def callback(self, *args: Any, stage: QueryStage, debater_name: DebaterName) -> None:
        if isinstance(self.parent, HasInterfaceObject):
            await self.parent.callback(*args, stage=stage, debater_name=debater_name)
        else:
            raise NotImplementedError()
