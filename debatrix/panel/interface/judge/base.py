from abc import ABC, abstractmethod

from ....core.common import DebateInfo, DimensionInfo, DimensionName, Speech, Verdict


class JudgeInterfaceABC(ABC):
    @abstractmethod
    async def create(self, dimension_name: DimensionName, dimension: DimensionInfo) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def reset(self, dimension_name: DimensionName, debate_info: DebateInfo) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def update(self, dimension_name: DimensionName, speech: Speech) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def judge(self, dimension_name: DimensionName) -> Verdict:
        raise NotImplementedError()
