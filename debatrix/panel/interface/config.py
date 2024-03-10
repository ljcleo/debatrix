from pydantic.dataclasses import dataclass

from .common import ParserConfig, VerdictExtractorConfig
from .judge import JudgeConfig
from .panel import PanelConfig


@dataclass(frozen=True, kw_only=True)
class PanelInterfaceConfig:
    parser_config: ParserConfig
    verdict_extractor_config: VerdictExtractorConfig
    judge_config: JudgeConfig
    panel_config: PanelConfig
