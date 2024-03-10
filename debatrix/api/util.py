from traceback import format_exception
from typing import Any, TypeVar

from pydantic import RootModel

T = TypeVar("T")


def pydantic_dump_json(obj: Any, /) -> str:
    return RootModel(obj).model_dump_json()


def pydantic_load_json(json: str, target: type[T], /) -> T:
    return RootModel[target].model_validate_json(json).root


def prettify_exception(e: BaseException) -> str:
    return "".join(format_exception(e))
