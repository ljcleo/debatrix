import enum
from typing import Self


def PrefixEnum(prefix: str, /) -> type[enum.StrEnum]:
    class PrefixEnum(enum.StrEnum):
        def __new__(cls, value: str) -> Self:
            value = f"{prefix}_{value}"
            obj = str.__new__(cls, value)
            obj._value_ = value
            return obj

    return PrefixEnum


class DebaterAction(PrefixEnum("part")):
    RESET = enum.auto()
    POLL = enum.auto()
    QUERY = enum.auto()
    UPDATE = enum.auto()


class JudgeAction(PrefixEnum("judge")):
    RESET = enum.auto()
    UPDATE = enum.auto()
    JUDGE = enum.auto()


class PanelAction(PrefixEnum("panel")):
    SUMMARIZE = enum.auto()


AllArenaActions = DebaterAction
AllPanelActions = JudgeAction | PanelAction
