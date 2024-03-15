from copy import deepcopy
from typing import Any

from ...record import RecorderConfig, RecorderHub
from ...resource.classes import RecorderConfigHub
from .util import pydantic_dump, pydantic_load


class RecorderConfigBuffer:
    def __init__(
        self, hub: RecorderConfigHub, process: RecorderHub, /, *, dump_after_update: bool = False
    ) -> None:
        self._hub = hub
        self._process = process
        self._dump_after_update = dump_after_update

        self._initial_config: RecorderConfig = self._hub.load()
        self._configs: dict[str, RecorderConfig] = {}

    def get_config_data(self, session_id: str, /) -> Any:
        return pydantic_dump(self._get_config(session_id))

    async def configure(self, session_id: str, /, *, config_data: Any | None = None) -> bool:
        config: RecorderConfig | None = (
            None if config_data is None else pydantic_load(config_data, RecorderConfig)
        )

        if dirty := (self._get_config(session_id) != config):
            if config is not None:
                self._configs[session_id] = config
                if self._dump_after_update:
                    self._hub.dump(config)

            self._process.get(session_id).config = self._get_config(session_id)

        return dirty

    def _get_config(self, session_id: str, /) -> RecorderConfig:
        if session_id not in self._configs:
            self._configs[session_id] = deepcopy(self._initial_config)

        return self._configs[session_id]
