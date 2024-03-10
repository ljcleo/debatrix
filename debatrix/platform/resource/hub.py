from pathlib import Path

from .classes import (
    ArenaInterfaceConfigHub,
    DimensionInfoHub,
    MotionHub,
    SpeechHub,
    DebateRecordHub,
    ModelConfigHub,
    PanelInterfaceConfigHub,
    PlatformConfigHub,
)


class ResourceHub:
    def __init__(self, resource_root: Path, /) -> None:
        self._motion = MotionHub(resource_root)
        self._speech = SpeechHub(resource_root)
        self._model_config = ModelConfigHub(resource_root)
        self._arena_interface_config = ArenaInterfaceConfigHub(resource_root)
        self._panel_interface_config = PanelInterfaceConfigHub(resource_root)
        self._dimension = DimensionInfoHub(resource_root)
        self._platform = PlatformConfigHub(resource_root)
        self._record = DebateRecordHub(resource_root)

    @property
    def motion(self) -> MotionHub:
        return self._motion

    @property
    def speech(self) -> SpeechHub:
        return self._speech

    @property
    def model_config(self) -> ModelConfigHub:
        return self._model_config

    @property
    def arena_interface_config(self) -> ArenaInterfaceConfigHub:
        return self._arena_interface_config

    @property
    def panel_interface_config(self) -> PanelInterfaceConfigHub:
        return self._panel_interface_config

    @property
    def dimension(self) -> DimensionInfoHub:
        return self._dimension

    @property
    def platform(self) -> PlatformConfigHub:
        return self._platform

    @property
    def record(self) -> DebateRecordHub:
        return self._record
