from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class RecorderConfig:
    verdict_only: bool
    include_prompts: bool
