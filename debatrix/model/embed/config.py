import enum

from pydantic.dataclasses import dataclass

from .openai import OpenAIEmbedModelConfig


@enum.unique
class EmbedModelBackend(enum.StrEnum):
    TEST = enum.auto()
    OPENAI = enum.auto()


@dataclass(frozen=True, kw_only=True)
class EmbedModelConfig:
    backend: EmbedModelBackend
    openai_config: OpenAIEmbedModelConfig
