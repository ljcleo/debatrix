from pathlib import Path

from ....manager import ManagerConfig
from .util import dump_yaml, load_yaml


class ManagerConfigHub:
    default_dir: Path = Path("config")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._config_dir: Path = resource_root / sub_dir

    def load(self) -> ManagerConfig:
        return load_yaml(dir=self._config_dir, name="manager", output_type=ManagerConfig)

    def dump(self, config: ManagerConfig, /) -> None:
        dump_yaml(config, dir=self._config_dir, name="manager")
