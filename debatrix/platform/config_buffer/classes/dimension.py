from typing import Any

from ....core.common import DimensionInfo, DimensionName
from ...process.classes import Manager
from ...resource.classes import DimensionInfoHub
from .util import pydantic_dump, pydantic_load

Dimensions = tuple[DimensionInfo, ...]


class DimensionInfoBuffer:
    def __init__(self, hub: DimensionInfoHub, process: Manager, /) -> None:
        self._hub = hub
        self._process = process
        self._load()

    @property
    def dimensions_data(self) -> Any:
        return pydantic_dump(list(self._dimensions))

    @property
    def valid_dimensions(self) -> Dimensions:
        return tuple(dimension for dimension in self._dimensions if dimension.weight >= 0)

    @property
    def dimensions_name(self) -> tuple[DimensionName, ...]:
        return tuple(dimension.name for dimension in self.valid_dimensions)

    def update_dimensions(self, *, dimensions_data: Any | None = None) -> bool:
        dimensions: Dimensions | None = (
            None if dimensions_data is None else pydantic_load(dimensions_data, Dimensions)
        )

        if dirty := (self._dimensions != dimensions):
            if dimensions is not None:
                self._dimensions = dimensions
                self._dump()

            self._process.update_dimensions(self.valid_dimensions)

        return dirty

    def _load(self) -> None:
        self._dimensions: Dimensions = self._hub.load()

    def _dump(self) -> None:
        self._hub.dump(self._dimensions)
