from typing import Any

from ....model import ModelConfig
from ...process.classes import Model
from ...resource.classes import ModelConfigHub
from .util import pydantic_dump, pydantic_load


class ModelConfigBuffer:
    def __init__(self, hub: ModelConfigHub, process: Model, /) -> None:
        self._hub = hub
        self._process = process
        self._load()

    @property
    def model_config_data(self) -> Any:
        return pydantic_dump(self._model_config)

    def update_model_config(self, *, config_data: Any | None = None) -> bool:
        config: ModelConfig | None = (
            None if config_data is None else pydantic_load(config_data, ModelConfig)
        )

        if dirty := (self._model_config != config):
            if config is not None:
                self._model_config = config
                self._dump()

            self._process.update_model_config(self._model_config)

        return dirty

    def _load(self) -> None:
        self._model_config: ModelConfig = self._hub.load()

    def _dump(self) -> None:
        self._hub.dump(self._model_config)
