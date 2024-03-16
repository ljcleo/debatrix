from collections.abc import Iterable
from pathlib import Path

from ...record import GroupedRecord
from .util import dump_yaml


class RecordHub:
    def __init__(self, resource_root: Path, /) -> None:
        self._dir: Path = resource_root / "record"

    def dump(self, name: str, records: Iterable[GroupedRecord], /) -> Path:
        return dump_yaml(list(records), dir=self._dir, name=name)
