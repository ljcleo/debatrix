from abc import ABC, abstractmethod
from typing import Generic, ParamSpec

from nicegui import ui

P = ParamSpec("P")


class BaseUI(ABC, Generic[P]):
    def __init__(self) -> None:
        self.refreshable: ui.refreshable[P, None] = ui.refreshable(self.init_ui)

    @abstractmethod
    def init_ui(self, *args: P.args, **kwargs: P.kwargs) -> None:
        raise NotImplementedError()

    def register_ui(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self.refreshable(*args, **kwargs)

    def refresh_ui(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self.refreshable.refresh(*args, **kwargs)
