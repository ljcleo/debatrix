from pathlib import Path

from ....core.common import DimensionInfo
from .util import dump_yaml, load_yaml


class DimensionInfoHub:
    default_dir: Path = Path("config")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._config_dir: Path = resource_root / sub_dir

    def load(self) -> tuple[DimensionInfo, ...]:
        return load_yaml(
            dir=self._config_dir, name="dimension", output_type=tuple[DimensionInfo, ...]
        )

    def dump(self, dimensions: tuple[DimensionInfo, ...], /) -> None:
        dump_yaml(dimensions, dir=self._config_dir, name="dimension")
