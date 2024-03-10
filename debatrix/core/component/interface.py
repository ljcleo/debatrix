from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Iterable
from functools import wraps
from typing import Any, Concatenate, Generic, ParamSpec, Self, TypeVar

from ...common import ANone
from ..common import DimensionalVerdict, Speech, Verdict

CP = ParamSpec("CP")
CT = TypeVar("CT")
QT = TypeVar("QT", str, Speech | None)


class WithCallback(ABC):
    added_cb: tuple[str, ...] = ()
    added_no_ret_cb: tuple[str, ...] = ()

    def __init_subclass__(
        cls,
        *,
        add_cb: str | Iterable[str] = (),
        add_no_ret_cb: str | Iterable[str] = (),
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)

        if isinstance(add_cb, str):
            add_cb = (add_cb,)
        if isinstance(add_no_ret_cb, str):
            add_no_ret_cb = (add_no_ret_cb,)

        cls.added_cb = tuple(set(cls.added_cb) | set(add_cb))
        cls.added_no_ret_cb = tuple(set(cls.added_no_ret_cb) | set(add_no_ret_cb))

        for names, decorator in (
            (add_cb, cls._add_cb),
            (add_no_ret_cb, cls._add_no_ret_cb),
        ):
            for name in names:
                backup_name: str = f"_{name}_raw"
                if name in cls.__dict__.keys():
                    setattr(cls, backup_name, getattr(cls, name))

                main_func: Callable[Concatenate[Self, ...], Any] = getattr(cls, backup_name)
                if not callable(main_func):
                    raise ValueError(name)

                pre_name: str = f"pre_{name}"
                post_name: str = f"post_{name}"
                pre_func: Any | None = getattr(cls, pre_name, None)
                post_func: Any | None = getattr(cls, post_name, None)

                for func_name, func in ((pre_name, pre_func), (post_name, post_func)):
                    if func is not None and not callable(func):
                        raise ValueError(func_name)

                setattr(cls, name, decorator(main_func, pre_func, post_func))

        @classmethod
        def init_sub(sub_cls: type[WithCallback], **kwargs: Any) -> None:
            for key in ("add_cb", "add_no_ret_cb"):
                if key not in kwargs.keys():
                    kwargs[key] = ()

            kwargs["add_cb"] = tuple(set(kwargs["add_cb"]) | set(cls.added_cb))
            kwargs["add_no_ret_cb"] = tuple(set(kwargs["add_no_ret_cb"]) | set(cls.added_no_ret_cb))
            super(cls, sub_cls).__init_subclass__(**kwargs)

        cls.__init_subclass__ = init_sub

    @classmethod
    def _add_cb(
        cls,
        main: Callable[Concatenate[Self, CP], Awaitable[CT]],
        pre: Callable[Concatenate[Self, CP], ANone] | None,
        post: Callable[Concatenate[Self, CT, CP], ANone] | None,
        /,
    ) -> Callable[Concatenate[Self, CP], Awaitable[CT]]:
        @wraps(main)
        async def wrapped(self: Self, *args: CP.args, **kwargs: CP.kwargs) -> CT:
            if pre is not None:
                await pre(self, *args, **kwargs)

            result: CT = await main(self, *args, **kwargs)
            if post is not None:
                await post(self, result, *args, **kwargs)

            return result

        return wrapped

    @classmethod
    def _add_no_ret_cb(
        cls,
        main: Callable[Concatenate[Self, CP], ANone],
        pre: Callable[Concatenate[Self, CP], ANone] | None,
        post: Callable[Concatenate[Self, CP], ANone] | None,
        /,
    ) -> Callable[Concatenate[Self, CP], ANone]:
        @wraps(main)
        async def wrapped(self: Self, *args: CP.args, **kwargs: CP.kwargs) -> None:
            if pre is not None:
                await pre(self, *args, **kwargs)

            await main(self, *args, **kwargs)
            if post is not None:
                await post(self, *args, **kwargs)

        return wrapped


class CanReset(WithCallback, add_no_ret_cb="reset"):
    @abstractmethod
    async def reset(self) -> None:
        raise NotImplementedError()


class CanPoll(WithCallback, add_cb="poll"):
    @abstractmethod
    async def poll(self) -> bool:
        raise NotImplementedError()


class CanQuery(WithCallback, Generic[QT], add_cb="query"):
    @abstractmethod
    async def query(self) -> QT:
        raise NotImplementedError()


class CanUpdate(WithCallback, add_no_ret_cb="update"):
    @abstractmethod
    async def update(self, *, speech: Speech) -> None:
        raise NotImplementedError()


class CanJudge(WithCallback, add_cb="judge"):
    @abstractmethod
    async def judge(self) -> Verdict:
        raise NotImplementedError()


class CanSummarize(WithCallback, add_cb="summarize"):
    @abstractmethod
    async def summarize(self, *, verdicts: Iterable[DimensionalVerdict]) -> Verdict:
        raise NotImplementedError()
