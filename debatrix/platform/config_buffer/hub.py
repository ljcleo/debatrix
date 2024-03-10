from ..process import ProcessHub
from ..resource import ResourceHub
from .classes import (
    ArenaInterfaceConfigBuffer,
    DimensionInfoBuffer,
    ModelConfigBuffer,
    PanelInterfaceConfigBuffer,
    PlatformConfigBuffer,
)


class ConfigBufferHub:
    def __init__(self, resource_hub: ResourceHub, process_hub: ProcessHub) -> None:
        self._model = ModelConfigBuffer(resource_hub.model_config, process_hub.model)

        self._arena_interface = ArenaInterfaceConfigBuffer(
            resource_hub.arena_interface_config, process_hub.arena_interface
        )

        self._panel_interface = PanelInterfaceConfigBuffer(
            resource_hub.panel_interface_config, process_hub.panel_interface
        )

        self._manager = DimensionInfoBuffer(resource_hub.dimension, process_hub.manager)
        self._platform = PlatformConfigBuffer(resource_hub.platform)

    @property
    def model(self) -> ModelConfigBuffer:
        return self._model

    @property
    def arena_interface(self) -> ArenaInterfaceConfigBuffer:
        return self._arena_interface

    @property
    def panel_interface(self) -> PanelInterfaceConfigBuffer:
        return self._panel_interface

    @property
    def manager(self) -> DimensionInfoBuffer:
        return self._manager

    @property
    def platform(self) -> PlatformConfigBuffer:
        return self._platform
