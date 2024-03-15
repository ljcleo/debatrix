from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class TestChatModelConfig:
    predict_delay: float
