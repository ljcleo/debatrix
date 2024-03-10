from pathlib import Path

from ...config import PlatformConfig
from .util import dump_yaml, load_yaml


class PlatformConfigHub:
    default_dir: Path = Path("config")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._config_dir: Path = resource_root / sub_dir

    def load(self) -> PlatformConfig:
        return load_yaml(dir=self._config_dir, name="platform", output_type=PlatformConfig)

    def dump(self, config: PlatformConfig, /) -> None:
        dump_yaml(config, dir=self._config_dir, name="platform")
