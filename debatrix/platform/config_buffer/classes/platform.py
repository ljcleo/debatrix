from typing import Any

from ...config import PlatformConfig
from ...resource.classes import PlatformConfigHub
from .util import pydantic_dump, pydantic_load


class PlatformConfigBuffer:
    def __init__(self, hub: PlatformConfigHub, /) -> None:
        self._hub = hub
        self._load()

    @property
    def platform_config_data(self) -> Any:
        return pydantic_dump(self._platform_config)

    @property
    def should_summarize(self) -> bool:
        return self._platform_config.should_summarize

    @property
    def record_prompts(self) -> bool:
        return self._platform_config.record_prompts

    @property
    def record_verdict_only(self) -> bool:
        return self._platform_config.record_verdict_only

    def update_platform_config(self, *, config_data: Any | None = None) -> bool:
        config: PlatformConfig | None = (
            None if config_data is None else pydantic_load(config_data, PlatformConfig)
        )

        if dirty := (self._platform_config != config):
            if config is not None:
                self._platform_config = config
                self._dump()

        return dirty

    def _load(self) -> None:
        self._platform_config: PlatformConfig = self._hub.load()

    def _dump(self) -> None:
        self._hub.dump(self._platform_config)
