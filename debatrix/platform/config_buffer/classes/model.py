from copy import deepcopy
from typing import Any

from ....model import ModelConfig
from ...process.classes import Model
from ...resource.classes import ModelConfigHub
from .util import pydantic_dump, pydantic_load


class ModelConfigBuffer:
    def __init__(
        self, hub: ModelConfigHub, process: Model, /, *, dump_after_update: bool = False
    ) -> None:
        self._hub = hub
        self._process = process
        self._dump_after_update = dump_after_update

        self._initial_config: ModelConfig = self._hub.load()
        self._configs: dict[str, ModelConfig] = {}

    def get_config_data(self, session_id: str, /) -> Any:
        return pydantic_dump(self._get_config(session_id))

    async def configure(self, session_id: str, /, *, config_data: Any | None = None) -> bool:
        config: ModelConfig | None = (
            None if config_data is None else pydantic_load(config_data, ModelConfig)
        )

        if dirty := (self._get_config(session_id) != config):
            if config is not None:
                self._configs[session_id] = config
                if self._dump_after_update:
                    self._hub.dump(config)

            await self._process.configure(session_id, config=self._get_config(session_id))

        return dirty

    def _get_config(self, session_id: str, /) -> ModelConfig:
        if session_id not in self._configs:
            self._configs[session_id] = deepcopy(self._initial_config)

        return self._configs[session_id]
