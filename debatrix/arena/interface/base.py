import re
from asyncio import sleep
from collections import defaultdict
from collections.abc import Iterable

from ...core.common import DebaterName, Speech
from ...util import tokenize
from .common import SpeechData, StreamingCallback
from .config import ArenaInterfaceConfig


class ArenaInterface:
    def __init__(self, *, callback: StreamingCallback | None = None) -> None:
        self._callback_func = callback

    def set_speeches(self, speeches: Iterable[SpeechData], /) -> None:
        self._speeches_debater_name: list[DebaterName] = []
        groups: defaultdict[DebaterName, list[str]] = defaultdict(list)

        for speech in speeches:
            self._speeches_debater_name.append(speech.debater_name)
            groups[speech.debater_name].append(re.sub("(?<!\\\\)\\\\\n", "  \n", speech.content))

        self._speeches: dict[DebaterName, tuple[str, ...]] = {
            debater_name: tuple(group) for debater_name, group in groups.items()
        }

        self._counter: dict[DebaterName, int] = {}

    @property
    def config(self) -> ArenaInterfaceConfig:
        return self._config

    @config.setter
    def config(self, config: ArenaInterfaceConfig) -> None:
        self._config = config

    async def reset(self, debater_name: DebaterName, /) -> None:
        self._counter[debater_name] = 0

    async def poll(self, debater_name: DebaterName, /) -> bool:
        return self._counter[debater_name] < len(self._speeches[debater_name])

    async def query(self, debater_name: DebaterName, /) -> str:
        if self._counter[debater_name] >= len(self._speeches[debater_name]):
            return ""

        speech: str = self._speeches[debater_name][self._counter[debater_name]]

        if self.config.streaming_delay == 0:
            await self._callback(speech, debater_name=debater_name)
        else:
            partial: str = ""

            for chunk in tokenize(speech, batch_size=self.config.streaming_chunk_size):
                await sleep(self.config.streaming_delay)
                partial += chunk
                await self._callback(chunk, debater_name=debater_name)

        await self._callback(None, debater_name=debater_name)
        return speech

    async def update(self, debater_name: DebaterName, /, *, speech: Speech) -> None:
        if speech.debater_name == debater_name:
            self._counter[debater_name] += 1

    async def _callback(self, chunk: str | None, /, *, debater_name: DebaterName) -> None:
        if self._callback_func is not None:
            await self._callback_func(debater_name, chunk)
