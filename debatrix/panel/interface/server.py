from ...api import APIServer, ServerInfo
from .config import PanelInterfaceConfig
from .judge import JudgeInterface
from .common import Helper, StreamingCallback
from .panel import PanelInterface


class PanelInterfaceServer(APIServer):
    def __init__(self, *, debug: bool = False, callback: StreamingCallback | None = None) -> None:
        super().__init__(debug=debug)

        self._helper = Helper(callback=callback)
        self._judge_interface = JudgeInterface(helper=self._helper)
        self._panel_interface = PanelInterface(helper=self._helper)

        self.assign("/judge/{dimension_name}/create", self._judge_interface.create)
        self.assign("/judge/{dimension_name}/reset", self._judge_interface.reset)
        self.assign("/judge/{dimension_name}/update", self._judge_interface.update)
        self.assign("/judge/{dimension_name}/judge", self._judge_interface.judge)

        self.assign("/panel/create", self._panel_interface.create)
        self.assign("/panel/reset", self._panel_interface.reset)
        self.assign("/panel/summarize", self._panel_interface.summarize)

    @property
    def config(self) -> PanelInterfaceConfig:
        return self._config

    @config.setter
    def config(self, config: PanelInterfaceConfig) -> None:
        self._config = config
        self._helper.parser_config = config.parser_config
        self._helper.verdict_extractor_config = config.verdict_extractor_config
        self._judge_interface.config = config.judge_config
        self._panel_interface.config = config.panel_config

    def set_model_server(self, *, server_info: ServerInfo) -> None:
        self._helper.set_model_server(server_info=server_info)

    async def close(self) -> None:
        await self._helper.close()
