from pathlib import Path

from ...record import RecorderConfig
from .util import dump_yaml, load_yaml


class RecorderConfigHub:
    default_dir: Path = Path("config")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._config_dir: Path = resource_root / sub_dir

    def load(self) -> RecorderConfig:
        return load_yaml(dir=self._config_dir, name="recorder", output_type=RecorderConfig)

    def dump(self, config: RecorderConfig, /) -> None:
        dump_yaml(config, dir=self._config_dir, name="recorder")
