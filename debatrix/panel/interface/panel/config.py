import enum

from pydantic import field_validator
from pydantic.dataclasses import dataclass

from ..common import TemplateInfo


@enum.unique
class PanelTemplateType(enum.StrEnum):
    SUMMARIZE = enum.auto()


PanelTemplates = tuple[TemplateInfo[PanelTemplateType], ...]


@dataclass(frozen=True, kw_only=True)
class PanelConfig:
    allow_concurrency: bool
    allow_ai_callback: bool
    common_system_prompt: str
    templates: PanelTemplates

    @field_validator("templates")
    @classmethod
    def templates_complete(cls, templates: PanelTemplates) -> PanelTemplates:
        assert {template.name for template in templates} == set(PanelTemplateType)
        return templates
