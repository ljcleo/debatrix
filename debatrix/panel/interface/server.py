from asyncio import TaskGroup
from functools import partial

from ...api import APIServer, ServerInfo
from ...core.action import AllPanelActions
from ...core.common import (
    DebateInfo,
    DimensionalVerdict,
    DimensionInfo,
    DimensionName,
    Speech,
    Verdict,
)
from .common import Helper
from .config import PanelInterfaceConfig
from .judge import JudgeInterface
from .panel import PanelInterface


class PanelInterfaceServer(APIServer):
    def __init__(self, *, debug: bool = False) -> None:
        super().__init__(debug=debug)

        self._interfaces: dict[str, tuple[Helper, JudgeInterface, PanelInterface]] = {}

        self.assign("/{session_id}/create", self._create)
        self.assign("/{session_id}/set_model", self._set_model)
        self.assign("/{session_id}/configure", self._configure)

        self.assign("/{session_id}/judge/{dimension_name}/create", self._judge_create)
        self.assign("/{session_id}/judge/{dimension_name}/reset", self._judge_reset)
        self.assign("/{session_id}/judge/{dimension_name}/update", self._judge_update)
        self.assign("/{session_id}/judge/{dimension_name}/judge", self._judge_judge)

        self.assign("/{session_id}/panel/create", self._panel_create)
        self.assign("/{session_id}/panel/reset", self._panel_reset)
        self.assign("/{session_id}/panel/summarize", self._panel_summarize)

    async def callback(
        self,
        action: AllPanelActions,
        dimension_name: DimensionName,
        message: tuple[str, str] | None,
        /,
        *,
        session_id: str,
    ) -> None:
        pass

    async def close(self) -> None:
        async with TaskGroup() as tg:
            for helper, _, _ in self._interfaces.values():
                tg.create_task(helper.close())

    async def _create(self, session_id: str) -> None:
        helper = Helper(
            session_id=session_id, callback=partial(self.callback, session_id=session_id)
        )

        self._interfaces[session_id] = (
            helper,
            JudgeInterface(helper=helper),
            PanelInterface(helper=helper),
        )

    async def _set_model(self, session_id: str, server_info: ServerInfo) -> None:
        self._interfaces[session_id][0].set_model_server(server_info=server_info)

    async def _configure(self, session_id: str, config: PanelInterfaceConfig) -> None:
        self._interfaces[session_id][0].parser_config = config.parser_config
        self._interfaces[session_id][0].verdict_extractor_config = config.verdict_extractor_config
        self._interfaces[session_id][1].config = config.judge_config
        self._interfaces[session_id][2].config = config.panel_config

    async def _judge_create(
        self, session_id: str, dimension_name: DimensionName, dimension: DimensionInfo
    ) -> None:
        await self._interfaces[session_id][1].create(dimension_name, dimension=dimension)

    async def _judge_reset(
        self, session_id: str, dimension_name: DimensionName, debate_info: DebateInfo
    ) -> None:
        await self._interfaces[session_id][1].reset(dimension_name, debate_info=debate_info)

    async def _judge_update(
        self, session_id: str, dimension_name: DimensionName, speech: Speech
    ) -> None:
        await self._interfaces[session_id][1].update(dimension_name, speech=speech)

    async def _judge_judge(self, session_id: str, dimension_name: DimensionName) -> Verdict:
        return await self._interfaces[session_id][1].judge(dimension_name)

    async def _panel_create(self, session_id: str) -> None:
        await self._interfaces[session_id][2].create()

    async def _panel_reset(self, session_id: str, debate_info: DebateInfo) -> None:
        await self._interfaces[session_id][2].reset(debate_info=debate_info)

    async def _panel_summarize(
        self, session_id: str, verdicts: list[DimensionalVerdict]
    ) -> Verdict:
        return await self._interfaces[session_id][2].summarize(verdicts=verdicts)
