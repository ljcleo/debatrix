from typing import Any

from ....arena import ArenaInterfaceConfig
from ...process.classes import ArenaInterface
from ...resource.classes import ArenaInterfaceConfigHub
from .util import pydantic_dump, pydantic_load


class ArenaInterfaceConfigBuffer:
    def __init__(self, hub: ArenaInterfaceConfigHub, process: ArenaInterface, /) -> None:
        self._hub = hub
        self._process = process
        self._load()

    @property
    def interface_config_data(self) -> Any:
        return pydantic_dump(self._interface_config)

    def update_arena_interface_config(self, *, config_data: Any | None = None) -> bool:
        config: ArenaInterfaceConfig | None = (
            None if config_data is None else pydantic_load(config_data, ArenaInterfaceConfig)
        )

        if dirty := (self._interface_config != config):
            if config is not None:
                self._interface_config = config
                self._dump()

            self._process.update_arena_interface_config(self._interface_config)

        return dirty

    def _load(self) -> None:
        self._interface_config: ArenaInterfaceConfig = self._hub.load()

    def _dump(self) -> None:
        self._hub.dump(self._interface_config)
