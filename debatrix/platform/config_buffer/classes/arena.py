from copy import deepcopy
from typing import Any

from ....arena import ArenaInterfaceConfig
from ...process.classes import ArenaInterface
from ...resource.classes import ArenaInterfaceConfigHub
from .util import pydantic_dump, pydantic_load


class ArenaInterfaceConfigBuffer:
    def __init__(
        self,
        hub: ArenaInterfaceConfigHub,
        process: ArenaInterface,
        /,
        *,
        dump_after_update: bool = False,
    ) -> None:
        self._hub = hub
        self._process = process
        self._dump_after_update = dump_after_update

        self._initial_config: ArenaInterfaceConfig = self._hub.load()
        self._configs: dict[str, ArenaInterfaceConfig] = {}

    def get_config_data(self, session_id: str, /) -> Any:
        return pydantic_dump(self._get_config(session_id))

    async def configure(self, session_id: str, /, *, config_data: Any | None = None) -> bool:
        config: ArenaInterfaceConfig | None = (
            None if config_data is None else pydantic_load(config_data, ArenaInterfaceConfig)
        )

        if dirty := (self._get_config(session_id) != config):
            if config is not None:
                self._configs[session_id] = config
                if self._dump_after_update:
                    self._hub.dump(config)

            await self._process.configure(session_id, config=self._get_config(session_id))

        return dirty

    def _get_config(self, session_id: str, /) -> ArenaInterfaceConfig:
        if session_id not in self._configs:
            self._configs[session_id] = deepcopy(self._initial_config)

        return self._configs[session_id]
