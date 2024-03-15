from pydantic.dataclasses import dataclass

from ..core.common import DimensionInfo


Dimensions = tuple[DimensionInfo, ...]


@dataclass
class ManagerConfig:
    should_summarize: bool
    dimensions: Dimensions
