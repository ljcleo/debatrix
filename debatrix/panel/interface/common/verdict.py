from typing import TypeVar

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

from ....core.common import DebateInfo, DebaterName
from ....model import ModelClient
from .parser import JSONParser
from .util import make_single_chat

T = TypeVar("T", bound=BaseModel)


class Score(BaseModel, title="Score for Specific Debater", frozen=True):
    score: int = Field(..., description="a score for the debater")


class JudgmentAndScore(BaseModel, title="Judgment and Score for Specific Debater", frozen=True):
    judgment: str = Field(..., description="judgment for the debater")
    score: int = Field(..., description="a score for the debater")


class Winner(BaseModel, title="Winner of Debate", frozen=True):
    winner: DebaterName = Field(..., description="the final winner of the debate")


@dataclass
class VerdictExtractorConfig:
    speech_prompt_template: str
    debater_prompt_template: str
    winner_prompt_template: str


class VerdictExtractor:
    @property
    def config(self) -> VerdictExtractorConfig:
        return self._config

    @config.setter
    def config(self, config: VerdictExtractorConfig) -> None:
        self._config = config

    async def get_speech_score(
        self,
        info: DebateInfo,
        debater_name: DebaterName,
        judgment: str,
        /,
        *,
        model: ModelClient,
        parser: JSONParser,
    ) -> int:
        return (
            await self._generate(
                self.config.speech_prompt_template,
                Score,
                model,
                parser,
                info=info,
                debater_name=debater_name,
                judgment=judgment,
            )
        ).score

    async def get_debater_score_and_judgment(
        self,
        info: DebateInfo,
        debater_name: DebaterName,
        judgment: str,
        /,
        *,
        model: ModelClient,
        parser: JSONParser,
    ) -> tuple[int, str]:
        judgment_and_score = await self._generate(
            self.config.debater_prompt_template,
            JudgmentAndScore,
            model,
            parser,
            info=info,
            debater_name=debater_name,
            judgment=judgment,
        )

        return judgment_and_score.score, judgment_and_score.judgment

    async def get_winner(
        self, info: DebateInfo, judgment: str, /, *, model: ModelClient, parser: JSONParser
    ) -> DebaterName:
        return DebaterName(
            (
                await self._generate(
                    self.config.winner_prompt_template,
                    Winner,
                    model,
                    parser,
                    info=info,
                    judgment=judgment,
                )
            ).winner
        )

    @staticmethod
    async def _generate(
        template: str, output_type: type[T], model: ModelClient, parser: JSONParser, /, **kwargs
    ) -> T:
        return await parser.parse(
            (
                await model.chat_predict(
                    messages=make_single_chat(
                        f"{template}\n\n{parser.make_schema_prompt(output_type)}", **kwargs
                    )
                )
            ).content,
            output_type,
            fix_model=model,
        )
