from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class OpenAIEmbedModelConfig:
    model: str
    api_key: str
    base_url: str
    proxy: str
