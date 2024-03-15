from uuid import uuid4

from ...core.action import AllPanelActions
from ...core.common import DimensionName, Speech
from .common import GroupedRecord
from .config import RecorderConfig


class Recorder:
    def __init__(self) -> None:
        self.reset()

    @property
    def config(self) -> RecorderConfig:
        return self._config

    @property
    def records(self) -> list[GroupedRecord]:
        return self._records

    @config.setter
    def config(self, config: RecorderConfig) -> None:
        self._config = config

    def reset(self) -> None:
        self._records: list[GroupedRecord] = []
        self._record_pos: dict[str, int] = {}

        self._panel_uuid: dict[tuple[AllPanelActions, DimensionName], str] = {}
        self._is_incomplete: dict[str, bool] = {}

    def add_speech(self, *, speech: Speech | None) -> None:
        if speech is not None and not self.config.verdict_only:
            self._update(self._register(), speech.debater_name, speech.content)

    def pre_add_comment(self, *, action: AllPanelActions, dimension_name: DimensionName) -> None:
        uuid: str = self._register()
        self._panel_uuid[action, dimension_name] = uuid
        self._is_incomplete[uuid] = False

    def is_append(
        self,
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
        chat_chunk: tuple[str, str],
    ) -> bool:
        uuid: str = self._panel_uuid[action, dimension_name]
        return chat_chunk[0] == "ai" and self._is_incomplete[uuid]

    def need_update(self, *, chat_chunk: tuple[str, str]) -> bool:
        return self.config.include_prompts or chat_chunk[0] in ("ai", "extra")

    def add_comment(
        self,
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
        chat_chunk: tuple[str, str] | None,
    ) -> None:
        if chat_chunk is not None:
            uuid: str = self._panel_uuid[action, dimension_name]
            name: str = f"{action.value}_AI"

            if dimension_name != "":
                name = f"{dimension_name}_{name}"

            source: str
            content: str
            source, content = chat_chunk

            append: bool = source == "ai" and self._is_incomplete[uuid]
            self._is_incomplete[uuid] = source == "ai"

            if self.config.include_prompts or source in ("ai", "extra"):
                self._update(uuid, name, content, append=append)

    def post_add_comment(self, *, action: AllPanelActions, dimension_name: DimensionName) -> None:
        del self._panel_uuid[action, dimension_name]

    def _register(self) -> str:
        return uuid4().hex

    def _update(self, uuid: str, source: str, content: str, /, *, append: bool = False) -> None:
        if uuid not in self._record_pos:
            self._record_pos[uuid] = len(self._records)
            self._records.append(GroupedRecord(source=source, content=[]))

        target = self.records[self._record_pos[uuid]]

        if not append or len(target.content) == 0:
            target.content.append(content)
        else:
            target.content[-1] += content

    @staticmethod
    def _get_name(action: AllPanelActions, dimension_name: DimensionName) -> str:
        name: str = f"{action.value}_AI"
        if dimension_name != "":
            name = f"{dimension_name}_{name}"

        return name


class RecorderHub:
    def __init__(self) -> None:
        self._recorders: dict[str, Recorder] = {}

    def create(self, session_id: str, /) -> None:
        self._recorders[session_id] = Recorder()

    def get(self, session_id: str, /) -> Recorder:
        return self._recorders[session_id]
