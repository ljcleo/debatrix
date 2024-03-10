import enum

from pydantic import field_validator
from pydantic.dataclasses import dataclass

from ..common import TemplateInfo


@enum.unique
class JudgeTemplateType(enum.StrEnum):
    UPDATE = enum.auto()
    JUDGE = enum.auto()


JudgeTemplates = tuple[TemplateInfo[JudgeTemplateType], ...]


@dataclass(frozen=True, kw_only=True)
class JudgeConfig:
    allow_concurrency: bool
    allow_ai_callback: bool
    skip_speech_judgement: bool
    analyze_speech: bool
    iterate_analysis: bool
    common_system_prompt: str
    templates: JudgeTemplates

    @field_validator("templates")
    @classmethod
    def templates_complete(cls, templates: JudgeTemplates) -> JudgeTemplates:
        assert {template.name for template in templates} == set(JudgeTemplateType)
        return templates
