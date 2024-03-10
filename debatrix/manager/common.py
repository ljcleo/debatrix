import enum


@enum.unique
class InterfaceType(enum.StrEnum):
    ARENA = enum.auto()
    PANEL = enum.auto()
