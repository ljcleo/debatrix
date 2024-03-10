import enum
from collections.abc import Callable
from typing import Concatenate

from ...common import ANone
from ...core.common import DebaterName


@enum.unique
class QueryStage(enum.StrEnum):
    PRE = enum.auto()
    POST = enum.auto()


TaskCallback = Callable[Concatenate[DebaterName, ...], ANone]
