from typing import Any, Generic, ParamSpec, TypeVar

from pydantic import RootModel
from pydantic.dataclasses import dataclass

T = TypeVar("T")
P = ParamSpec("P")


@dataclass(frozen=True, kw_only=True)
class APIResponse(Generic[T]):
    finished: bool
    cancelled: bool
    error: str | None
    result: T | None

    def to_dict(self) -> Any:
        return RootModel[APIResponse[T]](root=self).model_dump()


@dataclass(frozen=True, kw_only=True)
class ServerInfo:
    address: str
    sub_path: str | None = None
