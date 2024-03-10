from pathlib import Path

from ....core.common import DebateInfo
from .util import load_yaml


class MotionHub:
    default_dir: Path = Path("motion")

    def __init__(self, resource_root: Path, *, sub_dir: Path = default_dir) -> None:
        self._motions_dir: Path = resource_root / sub_dir
        self._motions_list_file: Path = self._motions_dir / "motion_list.txt"

    @property
    def all_motions(self) -> list[tuple[str, str]]:
        with self._motions_list_file.open(encoding="utf8") as f:
            return [
                (file, motion)
                for x in f
                if x.strip() != ""
                for file, _, motion in [x.strip().partition("\t")]
            ]

    def load(self, motion_id: str) -> DebateInfo:
        return load_yaml(dir=self._motions_dir, name=motion_id, output_type=DebateInfo)
