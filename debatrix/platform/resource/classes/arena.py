from pathlib import Path

from ....arena import ArenaInterfaceConfig
from .util import dump_yaml, load_yaml


class ArenaInterfaceConfigHub:
    default_dir: Path = Path("config")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._config_dir: Path = resource_root / sub_dir

    def load(self) -> ArenaInterfaceConfig:
        return load_yaml(dir=self._config_dir, name="arena", output_type=ArenaInterfaceConfig)

    def dump(self, config: ArenaInterfaceConfig, /) -> None:
        dump_yaml(config, dir=self._config_dir, name="arena")
