from typing import NewType

from pydantic.dataclasses import dataclass

DebaterName = NewType("DebaterName", str)


@dataclass(frozen=True, kw_only=True)
class DebaterInfo:
    name: DebaterName


@dataclass(frozen=True, kw_only=True)
class DebateInfo:
    motion: str
    pro_side: tuple[DebaterInfo, ...]
    con_side: tuple[DebaterInfo, ...]
    info_slide: str
    speech_order: tuple[DebaterName | None, ...]

    @property
    def all_debaters_info(self) -> tuple[DebaterInfo, ...]:
        return self.pro_side + self.con_side


@dataclass(frozen=True, kw_only=True)
class Speech:
    index: int
    index_by_debater: int
    debater_name: DebaterName
    content: str


DimensionName = NewType("DimensionName", str)


@dataclass(frozen=True, kw_only=True)
class DimensionPrompt:
    judge_debate: str
    analyze_speech: str
    use_previous: str
    judge_by_analysis: str


@dataclass(frozen=True, kw_only=True)
class DimensionInfo:
    name: DimensionName
    weight: int
    allow_tie: bool
    prompt: DimensionPrompt


@dataclass(frozen=True, kw_only=True)
class DebaterVerdict:
    debater_name: DebaterName
    score: int
    comment: str


@dataclass(frozen=True, kw_only=True)
class WinnerVerdict:
    winner: DebaterName
    comment: str


@dataclass(frozen=True, kw_only=True)
class Verdict:
    debaters_verdict: tuple[DebaterVerdict, ...]
    winner_verdict: WinnerVerdict


@dataclass(frozen=True, kw_only=True)
class DimensionalVerdict:
    dimension: DimensionInfo
    verdict: Verdict


@dataclass(frozen=True, kw_only=True)
class DebateResult:
    speeches: tuple[Speech, ...]
    dimensional_verdicts: tuple[DimensionalVerdict, ...]
    final_verdict: Verdict | None
