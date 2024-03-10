from typing import Any, TypeVar

from pydantic import RootModel

T = TypeVar("T")


def pydantic_dump(obj: Any, /) -> Any:
    return RootModel(obj).model_dump()


def pydantic_load(data: Any, target: type[T], /) -> T:
    return RootModel[target].model_validate(data).root
