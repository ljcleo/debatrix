from collections.abc import Iterable
from dataclasses import InitVar, dataclass
from typing import Any, Self, TypeVar

from ...api import ServerInfo
from ...core.action import AllPanelActions, JudgeAction, PanelAction
from ...core.common import DimensionInfo, DimensionName, DimensionalVerdict, Verdict, Speech
from ...core.component import BaseJudge, BasePanel
from ..interface import PanelInterfaceClient
from .base import HasInterfaceObject
from .common import Stage, TaskCallback

T = TypeVar("T")


@dataclass(kw_only=True)
class Judge(HasInterfaceObject, BaseJudge):
    async def reset(self) -> None:
        return await self.interface.judge_reset(self.dimension.name, debate_info=self.debate_info)

    async def pre_update(self: Self, *, speech: Speech) -> None:
        await self.callback(
            speech, action=JudgeAction.UPDATE, stage=Stage.PRE, dimension_name=self.dimension.name
        )

    async def update(self, *, speech: Speech) -> None:
        await self.interface.judge_update(self.dimension.name, speech=speech)

    async def post_update(self, *, speech: Speech) -> None:
        await self.callback(
            speech, action=JudgeAction.UPDATE, stage=Stage.POST, dimension_name=self.dimension.name
        )

    async def pre_judge(self) -> None:
        await self.callback(
            action=JudgeAction.JUDGE, stage=Stage.PRE, dimension_name=self.dimension.name
        )

    async def judge(self) -> Verdict:
        return await self.interface.judge_judge(self.dimension.name)

    async def post_judge(self, verdict: Verdict, /) -> None:
        await self.callback(
            verdict, action=JudgeAction.JUDGE, stage=Stage.POST, dimension_name=self.dimension.name
        )


@dataclass(kw_only=True)
class Panel(HasInterfaceObject, BasePanel[Judge]):
    pre_callback: InitVar[TaskCallback | None] = None
    post_callback: InitVar[TaskCallback | None] = None

    def __post_init__(
        self, pre_callback: TaskCallback | None, post_callback: TaskCallback | None
    ) -> None:
        self._interface = PanelInterfaceClient()
        self._callbacks: dict[Stage, TaskCallback] = {}

        if pre_callback is not None:
            self._callbacks[Stage.PRE] = pre_callback
        if post_callback is not None:
            self._callbacks[Stage.POST] = post_callback

    @property
    def interface(self) -> PanelInterfaceClient:
        return self._interface

    async def create_panel(self) -> None:
        await self.interface.panel_create()

    async def create_judge(self, *, dimension: DimensionInfo) -> Judge:
        await self.interface.judge_create(dimension.name, dimension=dimension)
        return Judge(parent=self)

    async def reset_panel(self) -> None:
        await self.interface.panel_reset(debate_info=self.debate_info)

    async def pre_summarize(self, *, verdicts: Iterable[DimensionalVerdict]) -> None:
        await self.callback(
            verdicts,
            action=PanelAction.SUMMARIZE,
            stage=Stage.PRE,
            dimension_name=DimensionName(""),
        )

    async def summarize(self, *, verdicts: Iterable[DimensionalVerdict]) -> Verdict:
        return await self.interface.panel_summarize(verdicts=verdicts)

    async def post_summarize(
        self, verdict: Verdict, /, *, verdicts: Iterable[DimensionalVerdict]
    ) -> None:
        await self.callback(
            verdict,
            verdicts,
            action=PanelAction.SUMMARIZE,
            stage=Stage.POST,
            dimension_name=DimensionName(""),
        )

    async def callback(
        self, *args: Any, action: AllPanelActions, stage: Stage, dimension_name: DimensionName
    ) -> None:
        cb: TaskCallback | None = self._callbacks.get(stage)
        if cb is not None:
            await cb(action, dimension_name, *args)

    def set_interface_server(self, *, server_info: ServerInfo) -> None:
        self.interface.set_server_info(server_info)

    async def close(self) -> None:
        await self.interface.close()
