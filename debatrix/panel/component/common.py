import enum
from collections.abc import Callable
from typing import Concatenate

from ...common import ANone
from ...core.action import AllPanelActions
from ...core.common import DimensionName


@enum.unique
class Stage(enum.StrEnum):
    PRE = enum.auto()
    IN = enum.auto()
    POST = enum.auto()


TaskCallback = Callable[Concatenate[AllPanelActions, DimensionName, ...], ANone]
