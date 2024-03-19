from pydantic.dataclasses import dataclass

from ..core.common import DimensionInfo


Dimensions = tuple[DimensionInfo, ...]


@dataclass(frozen=True, kw_only=True)
class ManagerConfig:
    should_summarize: bool
    dimensions: Dimensions
