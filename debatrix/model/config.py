from pydantic.dataclasses import dataclass

from .chat import ChatModelConfig
from .embed import EmbedModelConfig


@dataclass(frozen=True, kw_only=True)
class ModelConfig:
    chat_config: ChatModelConfig
    embed_config: EmbedModelConfig
