from dataclasses import dataclass

from ..common import DebateInfo


@dataclass(kw_only=True)
class DebateObject:
    parent: "DebateObject | None" = None

    @property
    def debate_info(self) -> DebateInfo:
        if isinstance(self.parent, DebateObject):
            return self.parent.debate_info
        else:
            raise NotImplementedError()
