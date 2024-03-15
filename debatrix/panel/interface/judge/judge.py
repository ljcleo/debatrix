from asyncio import Task
from typing import Any

from ....core.action import JudgeAction
from ....core.common import (
    DebateInfo,
    DebaterName,
    DebaterVerdict,
    DimensionInfo,
    DimensionName,
    Speech,
    Verdict,
    WinnerVerdict,
)
from ....model import ChatMessage, ChatRole
from ..common import (
    BiModeTaskGroup,
    Helper,
    InterfaceWithHelper,
    Memory,
    MemoryType,
    PromptTemplate,
)
from .base import JudgeInterfaceABC
from .config import JudgeConfig, JudgeTemplateType


class HelperJudgeWrapper:
    def __init__(
        self,
        helper: Helper,
        *,
        action: JudgeAction,
        dimension_name: DimensionName,
        templates: dict[JudgeTemplateType, PromptTemplate],
        allow_ai_callback: bool,
    ) -> None:
        self._helper = helper
        self._action = action
        self._dimension_name = dimension_name
        self._templates = templates
        self._allow_ai_callback = allow_ai_callback

    @property
    def info(self) -> DebateInfo:
        return self._helper.debate_info

    @property
    def memory(self) -> Memory:
        return self._helper.get_dimension_memory(self._dimension_name)

    def assign_speech_source(self, speech: Speech, /) -> str:
        return self._helper.assign_speech_source(self._dimension_name, speech)

    def get_debater_sources(self, debater_name: DebaterName, /) -> list[str]:
        return self._helper.get_debater_sources(self._dimension_name, debater_name)

    async def query(self, template_type: JudgeTemplateType, /, **kwargs: Any) -> str:
        return await self._helper.query(
            self._action,
            self._dimension_name,
            self._templates[template_type],
            self._allow_ai_callback,
            **kwargs,
        )

    async def callback(self, message: str, /) -> None:
        await self._helper.callback(
            ChatMessage(role=ChatRole.EXTRA, content=message),
            action=self._action,
            dimension_name=self._dimension_name,
        )

    async def close(self) -> None:
        await self._helper.callback(None, action=self._action, dimension_name=self._dimension_name)


class JudgeInterface(JudgeInterfaceABC, InterfaceWithHelper[JudgeTemplateType]):
    @property
    def config(self) -> JudgeConfig:
        return self._config

    @config.setter
    def config(self, config: JudgeConfig) -> None:
        self._config = config
        self.set_templates(config.templates, common_system_prompt=config.common_system_prompt)

    @property
    def allow_concurrency(self) -> bool:
        return self.config.allow_concurrency

    @property
    def allow_ai_callback(self) -> bool:
        return self.config.allow_ai_callback and not self.config.allow_concurrency

    @property
    def skip_speech_judgement(self) -> bool:
        return self.config.skip_speech_judgement

    @property
    def analyze_speech(self) -> bool:
        return self.config.analyze_speech

    @property
    def iterate_analysis(self) -> bool:
        return self.config.iterate_analysis and self.config.analyze_speech

    async def create(self, dimension_name: DimensionName, /, *, dimension: DimensionInfo) -> None:
        await self._helper.add_dimension(dimension_name, dimension)

    async def reset(self, dimension_name: DimensionName, /, *, debate_info: DebateInfo) -> None:
        await self._helper.get_dimension_memory(dimension_name).reset()

    async def update(self, dimension_name: DimensionName, /, *, speech: Speech) -> None:
        wrapped = HelperJudgeWrapper(
            self.helper,
            action=JudgeAction.UPDATE,
            dimension_name=dimension_name,
            templates=self._templates,
            allow_ai_callback=self.allow_ai_callback,
        )

        comment: str = await self.in_update(wrapped, speech=speech)
        score: int = 0

        if not self.skip_speech_judgement:
            score = await self.helper.get_speech_score(
                debater_name=speech.debater_name, judgment=comment
            )

        await wrapped.callback(f"# Comment\n\n{comment}")
        await wrapped.callback(f"# Temporary Score of {speech.debater_name}: {score}")
        await wrapped.close()

    async def judge(self, dimension_name: DimensionName, /) -> Verdict:
        wrapped = HelperJudgeWrapper(
            self.helper,
            action=JudgeAction.JUDGE,
            dimension_name=dimension_name,
            templates=self._templates,
            allow_ai_callback=self.allow_ai_callback,
        )

        judgment: str = await self.in_judge(wrapped)

        async with BiModeTaskGroup(concurrent=self.allow_concurrency) as tg:
            debater_tasks: list[Task[tuple[int, str]]] = [
                tg.create_task(
                    self.helper.get_debater_score_and_judgment(
                        debater_name=debater_info.name, judgment=judgment
                    )
                )
                for debater_info in self.helper.debate_info.all_debaters_info
            ]

            winner_task: Task[DebaterName] = tg.create_task(
                self.helper.get_winner(judgment=judgment)
            )

        debaters_verdict: tuple[DebaterVerdict, ...] = tuple(
            DebaterVerdict(debater_name=debater_info.name, score=score, comment=comment)
            for debater_info, (score, comment) in zip(
                self.helper.debate_info.all_debaters_info, [task.result() for task in debater_tasks]
            )
        )

        winner_verdict = WinnerVerdict(winner=winner_task.result(), comment=judgment)

        for debater_verdict in debaters_verdict:
            await wrapped.callback(
                f"# Score of {debater_verdict.debater_name}: {debater_verdict.score}\n\n"
                f"{debater_verdict.comment}"
            )

        await wrapped.callback(f"# Winner: {winner_verdict.winner}\n\n{winner_verdict.comment}")
        await wrapped.close()
        return Verdict(debaters_verdict=debaters_verdict, winner_verdict=winner_verdict)

    async def in_update(self, wrapped: HelperJudgeWrapper, /, *, speech: Speech) -> str:
        memory: Memory = wrapped.memory
        prev_speeches: list[tuple[str, str]] = self._fetch(memory, analysis=False)
        prev_analyses: list[tuple[str, str]] = self._fetch(memory, analysis=True)

        new_speech_source: str = wrapped.assign_speech_source(speech)
        await memory.add_speech(speech, source=wrapped.assign_speech_source(speech), cut=False)

        analysis: str = ""

        if not self.skip_speech_judgement or self.analyze_speech:
            analysis = await wrapped.query(
                JudgeTemplateType.UPDATE,
                prev_content=prev_analyses if self.iterate_analysis else prev_speeches,
                is_prev_analyses=self.iterate_analysis,
                new_speech=speech,
            )

        await memory.add_analyses([analysis], source=new_speech_source)
        return analysis

    async def in_judge(self, wrapped: HelperJudgeWrapper, /) -> str:
        memory: Memory = wrapped.memory
        speeches: list[tuple[str, str]] = self._fetch(memory, analysis=False)
        analyses: list[tuple[str, str]] = self._fetch(memory, analysis=True)

        return await wrapped.query(
            JudgeTemplateType.JUDGE,
            debate_content=analyses if self.analyze_speech else speeches,
            is_content_analyses=self.analyze_speech,
        )

    def _fetch(self, memory: Memory, /, *, analysis: bool) -> list[tuple[str, str]]:
        return memory.fetch(
            include_types=MemoryType.ANALYSIS if analysis else MemoryType.SPEECH, format_source=True
        )
