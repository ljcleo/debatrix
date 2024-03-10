from uuid import uuid4

from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class GroupedRecord:
    source: str
    content: list[str]


class DebateRecord:
    def __init__(self) -> None:
        self.reset()

    @property
    def records(self) -> list[GroupedRecord]:
        return self._records

    def reset(self) -> None:
        self._records: list[GroupedRecord] = []
        self._record_pos: dict[str, int] = {}

    def get(self, uuid: str, /) -> GroupedRecord | None:
        return None if uuid not in self._record_pos else self.records[self._record_pos[uuid]]

    def register(self) -> str:
        return uuid4().hex

    def update(self, uuid: str, source: str, content: str, /, *, append: bool = False) -> None:
        if uuid not in self._record_pos:
            self._record_pos[uuid] = len(self._records)
            self._records.append(GroupedRecord(source=source, content=[]))

        target = self.records[self._record_pos[uuid]]

        if not append or len(target.content) == 0:
            target.content.append(content)
        else:
            target.content[-1] += content
