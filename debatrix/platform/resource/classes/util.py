from pathlib import Path
from typing import Any, TypeVar

from pydantic import RootModel
from yaml import safe_dump, safe_load

T = TypeVar("T")


def list_all_yaml(*, dir: Path) -> list[str]:
    return sorted(file.stem for file in dir.iterdir() if file.suffix == ".yml")


def load_yaml(*, dir: Path, name: str, output_type: type[T]) -> T:
    with (dir / f"{name}.yml").open(encoding="utf8") as f:
        return RootModel[output_type].model_validate(safe_load(f)).root


def dump_yaml(obj: Any, /, *, dir: Path, name: str) -> None:
    dir.mkdir(exist_ok=True)

    with (dir / f"{name}.yml").open("w", encoding="utf8") as f:
        safe_dump(
            RootModel(obj).model_dump(mode="json"), f, default_flow_style=False, sort_keys=False
        )
