from pathlib import Path

from .classes import (
    ArenaInterfaceConfigHub,
    ManagerConfigHub,
    ModelConfigHub,
    MotionHub,
    PanelInterfaceConfigHub,
    RecorderConfigHub,
    RecordHub,
    SpeechHub,
)


class ResourceHub:
    def __init__(self, resource_root: Path, /) -> None:
        self._motion = MotionHub(resource_root)
        self._speech = SpeechHub(resource_root)
        self._model_config = ModelConfigHub(resource_root)
        self._arena_interface_config = ArenaInterfaceConfigHub(resource_root)
        self._panel_interface_config = PanelInterfaceConfigHub(resource_root)
        self._manager_config = ManagerConfigHub(resource_root)
        self._recorder_config = RecorderConfigHub(resource_root)
        self._record = RecordHub(resource_root)

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
    def manager_config(self) -> ManagerConfigHub:
        return self._manager_config

    @property
    def recorder_config(self) -> RecorderConfigHub:
        return self._recorder_config

    @property
    def record(self) -> RecordHub:
        return self._record
