from typing import Any, Generic, TypeVar

from pydantic import field_validator
from pydantic.dataclasses import dataclass

from ....model import ChatMessage, ChatRole
from .util import format_jinja2

T = TypeVar("T", bound=str)


@dataclass(frozen=True, kw_only=True)
class MessageTemplate:
    role: ChatRole
    content: str

    @field_validator("role")
    @classmethod
    def role_not_extra(cls, v: ChatRole) -> ChatRole:
        assert v != ChatRole.EXTRA
        return v

    def format(self, **kwargs: Any) -> ChatMessage:
        return ChatMessage(role=self.role, content=format_jinja2(self.content, **kwargs))


PromptTemplate = tuple[MessageTemplate, ...]


@dataclass(frozen=True, kw_only=True)
class TemplateInfo(Generic[T]):
    name: T
    messages: PromptTemplate
