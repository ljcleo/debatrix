from copy import deepcopy
from typing import Any

from ....core.common import DimensionInfo
from ....manager import ManagerConfig
from ...process.classes import Manager
from ...resource.classes import ManagerConfigHub
from .util import pydantic_dump, pydantic_load


class ManagerConfigBuffer:
    def __init__(
        self, hub: ManagerConfigHub, process: Manager, /, *, dump_after_update: bool = False
    ) -> None:
        self._hub = hub
        self._process = process
        self._dump_after_update = dump_after_update

        self._initial_config: ManagerConfig = self._hub.load()
        self._configs: dict[str, ManagerConfig] = {}

    def get_config_data(self, session_id: str, /) -> Any:
        return pydantic_dump(self._get_config(session_id))

    def get_valid_dimensions(self, session_id: str, /) -> tuple[DimensionInfo, ...]:
        return tuple(
            dimension
            for dimension in self._get_config(session_id).dimensions
            if dimension.weight >= 0
        )

    def get_verdict_count(self, session_id: str, /) -> int:
        return len(self.get_valid_dimensions(session_id)) + int(
            self._get_config(session_id).should_summarize
        )

    async def configure(self, session_id: str, /, *, config_data: Any | None = None) -> bool:
        config: ManagerConfig | None = (
            None if config_data is None else pydantic_load(config_data, ManagerConfig)
        )

        if dirty := (self._get_config(session_id) != config):
            if config is not None:
                self._configs[session_id] = config
                if self._dump_after_update:
                    self._hub.dump(config)

            await self._process.configure(
                session_id,
                config=ManagerConfig(
                    should_summarize=self._get_config(session_id).should_summarize,
                    dimensions=self.get_valid_dimensions(session_id),
                ),
            )

        return dirty

    def _get_config(self, session_id: str, /) -> ManagerConfig:
        if session_id not in self._configs:
            self._configs[session_id] = deepcopy(self._initial_config)

        return self._configs[session_id]
