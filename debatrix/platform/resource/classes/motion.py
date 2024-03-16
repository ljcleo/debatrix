from pathlib import Path

from ....core.common import DebateInfo
from .util import load_yaml


class MotionHub:
    def __init__(self, resource_root: Path, /) -> None:
        self._dir: Path = resource_root / "motion"
        self._motion_list_file: Path = self._dir / "motion_list.txt"

    @property
    def all_motions(self) -> list[tuple[str, str]]:
        with self._motion_list_file.open(encoding="utf8") as f:
            return [
                (file, motion)
                for x in f
                if x.strip() != ""
                for file, _, motion in [x.strip().partition("\t")]
            ]

    def load(self, motion_id: str, /) -> DebateInfo:
        return load_yaml(dir=self._dir, name=motion_id, output_type=DebateInfo)
