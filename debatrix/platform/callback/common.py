import enum


@enum.unique
class CallbackStage(enum.IntEnum):
    PRE = enum.auto()
    IN = enum.auto()
    POST = enum.auto()
