from pathlib import Path

from ....panel import PanelInterfaceConfig
from .util import dump_yaml, load_yaml


class PanelInterfaceConfigHub:
    default_dir: Path = Path("config")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._config_dir: Path = resource_root / sub_dir

    def load(self) -> PanelInterfaceConfig:
        return load_yaml(dir=self._config_dir, name="panel", output_type=PanelInterfaceConfig)

    def dump(self, config: PanelInterfaceConfig, /) -> None:
        dump_yaml(config, dir=self._config_dir, name="panel")
