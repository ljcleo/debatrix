from pathlib import Path

from ....arena import SpeechData
from .util import load_yaml


class SpeechHub:
    default_dir: Path = Path("speech")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._speeches_dir: Path = resource_root / sub_dir

    def load(self, motion_id: str, /) -> list[SpeechData]:
        return load_yaml(dir=self._speeches_dir, name=motion_id, output_type=list[SpeechData])
