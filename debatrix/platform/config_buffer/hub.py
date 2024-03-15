from ..process import ProcessHub
from ..resource import ResourceHub
from ..record import RecorderHub
from .classes import (
    ArenaInterfaceConfigBuffer,
    ManagerConfigBuffer,
    ModelConfigBuffer,
    PanelInterfaceConfigBuffer,
    RecorderConfigBuffer,
)


class ConfigBufferHub:
    def __init__(
        self,
        resource_hub: ResourceHub,
        process_hub: ProcessHub,
        recorder_hub: RecorderHub,
        /,
        *,
        dump_after_update: bool = False,
    ) -> None:
        self._model = ModelConfigBuffer(
            resource_hub.model_config, process_hub.model, dump_after_update=dump_after_update
        )

        self._arena_interface = ArenaInterfaceConfigBuffer(
            resource_hub.arena_interface_config,
            process_hub.arena_interface,
            dump_after_update=dump_after_update,
        )

        self._panel_interface = PanelInterfaceConfigBuffer(
            resource_hub.panel_interface_config,
            process_hub.panel_interface,
            dump_after_update=dump_after_update,
        )

        self._manager = ManagerConfigBuffer(
            resource_hub.manager_config, process_hub.manager, dump_after_update=dump_after_update
        )

        self._recorder = RecorderConfigBuffer(
            resource_hub.recorder_config, recorder_hub, dump_after_update=dump_after_update
        )

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
    def manager(self) -> ManagerConfigBuffer:
        return self._manager

    @property
    def recorder(self) -> RecorderConfigBuffer:
        return self._recorder
