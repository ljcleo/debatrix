from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class TestChatModelConfig:
    streaming_delay: float
    direct_delay: float
