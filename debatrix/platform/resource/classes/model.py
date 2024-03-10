from pathlib import Path

from ....model import ModelConfig
from .util import dump_yaml, load_yaml


class ModelConfigHub:
    default_dir: Path = Path("config")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._config_dir: Path = resource_root / sub_dir

    def load(self) -> ModelConfig:
        return load_yaml(dir=self._config_dir, name="model", output_type=ModelConfig)

    def dump(self, configs: ModelConfig, /) -> None:
        dump_yaml(configs, dir=self._config_dir, name="model")
