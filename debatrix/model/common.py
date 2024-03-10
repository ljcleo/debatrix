import enum
from typing import overload
from collections.abc import Iterator

from pydantic import RootModel
from pydantic.dataclasses import dataclass


@enum.unique
class ChatRole(enum.StrEnum):
    SYSTEM = enum.auto()
    HUMAN = enum.auto()
    AI = enum.auto()
    EXTRA = enum.auto()


@dataclass(frozen=True, kw_only=True)
class ChatMessage:
    role: ChatRole
    content: str

    def __add__(self, other: "ChatMessage") -> "ChatMessage":
        return ChatMessage(role=self.role, content=self.content + other.content)


class ChatHistory(RootModel[tuple[ChatMessage, ...]]):
    root: tuple[ChatMessage, ...]

    def __len__(self) -> int:
        return len(self.root)

    def __iter__(self) -> Iterator[ChatMessage]:
        return iter(self.root)

    @overload
    def __getitem__(self, index: int) -> ChatMessage:
        pass

    @overload
    def __getitem__(self, index: slice) -> "ChatHistory":
        pass

    def __getitem__(self, index: int | slice) -> "ChatMessage | ChatHistory":
        if isinstance(index, slice):
            return ChatHistory(root=self.root[index])
        else:
            return self.root[index]
