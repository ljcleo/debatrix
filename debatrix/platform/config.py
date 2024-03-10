from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class PlatformConfig:
    should_summarize: bool
    record_verdict_only: bool
    record_prompts: bool
