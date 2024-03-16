from pathlib import Path

from ....arena import SpeechData
from .util import load_yaml


class SpeechHub:
    def __init__(self, resource_root: Path, /) -> None:
        self._dir: Path = resource_root / "speech"

    def load(self, motion_id: str, /) -> list[SpeechData]:
        return load_yaml(dir=self._dir, name=motion_id, output_type=list[SpeechData])
