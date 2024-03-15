from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class GroupedRecord:
    source: str
    content: list[str]
