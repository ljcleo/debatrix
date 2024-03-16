from pathlib import Path

from .classes import ConfigHub, MotionHub, RecordHub, SpeechHub


class ResourceHub:
    def __init__(self, resource_root: Path, /) -> None:
        self._config = ConfigHub(resource_root)
        self._motion = MotionHub(resource_root)
        self._speech = SpeechHub(resource_root)
        self._record = RecordHub(resource_root)

    @property
    def config(self) -> ConfigHub:
        return self._config

    @property
    def motion(self) -> MotionHub:
        return self._motion

    @property
    def speech(self) -> SpeechHub:
        return self._speech

    @property
    def record(self) -> RecordHub:
        return self._record
