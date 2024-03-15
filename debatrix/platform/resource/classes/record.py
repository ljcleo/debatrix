from collections.abc import Iterable
from pathlib import Path

from ...record import GroupedRecord
from .util import dump_yaml


class RecordHub:
    default_dir: Path = Path("record")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._record_dir: Path = resource_root / sub_dir

    def dump(self, name: str, records: Iterable[GroupedRecord], /) -> Path:
        return dump_yaml(list(records), dir=self._record_dir, name=name)
