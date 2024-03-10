from abc import ABC, abstractmethod

from ....core.common import DebateInfo, DimensionalVerdict, Verdict


class PanelInterfaceABC(ABC):
    @abstractmethod
    async def create(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def reset(self, debate_info: DebateInfo) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def summarize(self, verdicts: list[DimensionalVerdict]) -> Verdict:
        raise NotImplementedError()
