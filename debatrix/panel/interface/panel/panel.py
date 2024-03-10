from asyncio import Task
from typing import Any, TypeVar

from pydantic import BaseModel

from ....core.action import PanelAction
from ....core.common import (
    DebateInfo,
    DebaterVerdict,
    DimensionalVerdict,
    DimensionInfo,
    DimensionName,
    Verdict,
    WinnerVerdict,
)
from ....model import ChatMessage, ChatRole
from ..common import BiModeTaskGroup, Helper, InterfaceWithHelper, PromptTemplate
from .base import PanelInterfaceABC
from .config import PanelConfig, PanelTemplateType

DT = TypeVar("DT", bound=BaseModel)


class HelperPanelWrapper:
    def __init__(
        self,
        helper: Helper,
        *,
        action: PanelAction,
        templates: dict[PanelTemplateType, PromptTemplate],
        allow_ai_callback: bool,
    ) -> None:
        self._helper = helper
        self._action = action
        self._templates = templates
        self._allow_ai_callback = allow_ai_callback

    @property
    def info(self) -> DebateInfo:
        return self._helper.debate_info

    async def query(self, template_type: PanelTemplateType, /, **kwargs: Any) -> str:
        return await self._helper.query(
            self._action, None, self._templates[template_type], self._allow_ai_callback, **kwargs
        )

    async def callback(self, message: str, /) -> None:
        await self._helper.callback(
            ChatMessage(role=ChatRole.EXTRA, content=message),
            action=self._action,
            dimension_name=DimensionName(""),
        )

    async def close(self) -> None:
        await self._helper.callback(None, action=self._action, dimension_name=DimensionName(""))


class PanelInterface(PanelInterfaceABC, InterfaceWithHelper[PanelTemplateType]):
    @property
    def config(self) -> PanelConfig:
        return self._config

    @config.setter
    def config(self, config: PanelConfig) -> None:
        self._config = config
        self.set_templates(config.templates, common_system_prompt=config.common_system_prompt)

    @property
    def allow_concurrency(self) -> bool:
        return self.config.allow_concurrency

    @property
    def allow_ai_callback(self) -> bool:
        return self.config.allow_ai_callback and not self.config.allow_concurrency

    async def create(self) -> None:
        await self._helper.reset_dimensions()

    async def reset(self, debate_info: DebateInfo) -> None:
        await self._helper.set_debate_info(debate_info)

    async def summarize(self, verdicts: list[DimensionalVerdict]) -> Verdict:
        wrapped = HelperPanelWrapper(
            self.helper,
            action=PanelAction.SUMMARIZE,
            templates=self._templates,
            allow_ai_callback=self.allow_ai_callback,
        )

        judgment: str = await self.in_summarize(wrapped, verdicts=verdicts)

        async with BiModeTaskGroup(concurrent=self.allow_concurrency) as tg:
            debater_tasks: list[Task[tuple[int, str]]] = [
                tg.create_task(
                    self.helper.get_debater_score_and_judgment(
                        debater_name=debater_info.name, judgment=judgment
                    )
                )
                for debater_info in self.helper.debate_info.all_debaters_info
            ]

            winner_task: Task[str] = tg.create_task(self.helper.get_winner(judgment=judgment))

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

    async def in_summarize(
        self, wrapped: HelperPanelWrapper, /, *, verdicts: list[DimensionalVerdict]
    ) -> str:
        map: dict[DimensionInfo, str] = {
            verdict.dimension: verdict.verdict.winner_verdict.comment for verdict in verdicts
        }

        return await wrapped.query(
            PanelTemplateType.SUMMARIZE,
            verdicts=[(dimension, map[dimension]) for dimension in self.helper.dimensions],
        )
