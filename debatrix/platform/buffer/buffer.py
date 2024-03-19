from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from ...core.common import DimensionInfo
from ...manager import ManagerConfig
from ..config import Config
from ..process import ProcessHub
from ..record import RecorderHub
from ..resource.classes import ConfigHub
from .util import pydantic_dump, pydantic_load


class ConfigBuffer:
    def __init__(
        self,
        config_hub: ConfigHub,
        process_hub: ProcessHub,
        recorder_hub: RecorderHub,
        /,
        *,
        dump_after_update: bool = False,
    ) -> None:
        self._config_hub = config_hub
        self._process_hub = process_hub
        self._recorder_hub = recorder_hub
        self._dump_after_update = dump_after_update

        self._initial_config: Config = self._config_hub.load()
        self._configs: dict[str, Config] = {}

    def get_config_data(self, session_id: str, /) -> Any:
        return pydantic_dump(self._get_config(session_id))

    def get_valid_dimensions(self, session_id: str, /) -> tuple[DimensionInfo, ...]:
        return self._get_valid_dimensions(
            dimensions=self._get_config(session_id).manager.dimensions
        )

    def get_verdict_count(self, session_id: str, /) -> int:
        valid_config: ManagerConfig = self._get_valid_manager_config(
            config=self._get_config(session_id).manager
        )

        return len(valid_config.dimensions) + int(valid_config.should_summarize)

    async def configure(self, session_id: str, /, *, config_data: Any | None = None) -> bool:
        config: Config | None = None if config_data is None else pydantic_load(config_data, Config)

        if dirty := (self._get_config(session_id) != config):
            if config is not None:
                self._configs[session_id] = config
                if self._dump_after_update:
                    self._config_hub.dump(config)

            cur_config: Config = self._get_config(session_id)
            await self._process_hub.model_configure(session_id, config=cur_config.model)
            await self._process_hub.arena_configure(session_id, config=cur_config.arena)
            await self._process_hub.panel_configure(session_id, config=cur_config.panel)

            await self._process_hub.manager_configure(
                session_id, config=self._get_valid_manager_config(config=cur_config.manager)
            )

            self._recorder_hub.get(session_id).config = cur_config.recorder

        return dirty

    def _get_config(self, session_id: str, /) -> Config:
        if session_id not in self._configs:
            self._configs[session_id] = deepcopy(self._initial_config)

        return self._configs[session_id]

    @staticmethod
    def _get_valid_manager_config(*, config: ManagerConfig) -> ManagerConfig:
        return ManagerConfig(
            should_summarize=config.should_summarize,
            dimensions=ConfigBuffer._get_valid_dimensions(dimensions=config.dimensions),
        )

    @staticmethod
    def _get_valid_dimensions(*, dimensions: Iterable[DimensionInfo]) -> tuple[DimensionInfo, ...]:
        return tuple(dimension for dimension in dimensions if dimension.weight >= 0)
