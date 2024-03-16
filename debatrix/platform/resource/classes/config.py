from pathlib import Path

from ....arena.interface.config import ArenaInterfaceConfig
from ....manager.config import ManagerConfig
from ....model.config import ModelConfig
from ....panel.interface.config import PanelInterfaceConfig
from ...record.config import RecorderConfig
from ...config import Config
from .util import dump_yaml, load_yaml


class ConfigHub:
    def __init__(self, resource_root: Path, /) -> None:
        self._dir: Path = resource_root / "config"

    def load(self) -> Config:
        return Config(
            model=load_yaml(dir=self._dir, name="model", output_type=ModelConfig),
            arena=load_yaml(dir=self._dir, name="arena", output_type=ArenaInterfaceConfig),
            panel=load_yaml(dir=self._dir, name="panel", output_type=PanelInterfaceConfig),
            manager=load_yaml(dir=self._dir, name="manager", output_type=ManagerConfig),
            recorder=load_yaml(dir=self._dir, name="recorder", output_type=RecorderConfig),
        )

    def dump(self, config: Config, /) -> None:
        dump_yaml(config.model, dir=self._dir, name="model")
        dump_yaml(config.arena, dir=self._dir, name="arena")
        dump_yaml(config.panel, dir=self._dir, name="panel")
        dump_yaml(config.model, dir=self._dir, name="manager")
        dump_yaml(config.recorder, dir=self._dir, name="recorder")
