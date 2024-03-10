import enum

from pydantic.dataclasses import dataclass

from .openai import OpenAIChatModelConfig
from .test import TestChatModelConfig


@enum.unique
class ChatModelBackend(enum.StrEnum):
    TEST = enum.auto()
    OPENAI = enum.auto()


@dataclass(frozen=True, kw_only=True)
class ChatModelConfig:
    backend: ChatModelBackend
    test_config: TestChatModelConfig
    openai_config: OpenAIChatModelConfig
