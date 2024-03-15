from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Generic, Iterable, TypeVar

from ....api import ServerInfo
from ....core.action import AllPanelActions
from ....core.common import DebateInfo, DebaterName, DimensionInfo, DimensionName, Speech
from ....model import ChatHistory, ChatMessage, ModelClient, ChatRole
from ....util import sanitize
from .common import StreamingCallback
from .memory import Memory
from .parser import JSONParser, ParserConfig
from .template import MessageTemplate, PromptTemplate, TemplateInfo
from .verdict import VerdictExtractor, VerdictExtractorConfig

T = TypeVar("T", bound=str)


class Helper:
    def __init__(self, *, session_id: str, callback: StreamingCallback | None = None) -> None:
        self._callback_func = callback

        self._model = ModelClient(session_id=session_id)

        self._parser = JSONParser()
        self._verdict_extractor = VerdictExtractor()

        self._dimensions: dict[DimensionName, DimensionInfo] = {}
        self._memories: dict[DimensionName, Memory] = {}
        self._sources: dict[DimensionName, defaultdict[DebaterName, list[str]]] = {}

    @property
    def parser_config(self) -> ParserConfig:
        return self._parser.config

    @property
    def verdict_extractor_config(self) -> VerdictExtractorConfig:
        return self._verdict_extractor.config

    @property
    def dimensions(self) -> list[DimensionInfo]:
        return sorted(self._dimensions.values(), key=lambda x: (-x.weight, x.name))

    @property
    def debate_info(self) -> DebateInfo:
        return self._debate_info

    @parser_config.setter
    def parser_config(self, config: ParserConfig) -> None:
        self._parser.config = config

    @verdict_extractor_config.setter
    def verdict_extractor_config(self, config: VerdictExtractorConfig) -> None:
        self._verdict_extractor.config = config

    def set_model_server(self, *, server_info: ServerInfo) -> None:
        self._model.set_server_info(server_info)

    async def reset_dimensions(self) -> None:
        self._dimensions.clear()
        self._memories.clear()
        self._sources.clear()

    async def add_dimension(
        self, dimension_name: DimensionName, dimension: DimensionInfo, /
    ) -> None:
        self._dimensions[dimension_name] = dimension
        self._memories[dimension_name] = Memory(model=self._model)
        self._sources[dimension_name] = defaultdict(list)

    async def set_debate_info(self, debate_info: DebateInfo, /) -> None:
        self._debate_info = debate_info

    def get_dimension_memory(self, dimension_name: DimensionName, /) -> Memory:
        return self._memories[dimension_name]

    def assign_speech_source(self, dimension_name: DimensionName, new_speech: Speech, /) -> str:
        source: str = f"Speech {new_speech.index} by {new_speech.debater_name}"
        self._sources[dimension_name][new_speech.debater_name].append(source)
        return source

    def get_debater_sources(
        self, dimension_name: DimensionName, debater_name: DebaterName, /
    ) -> list[str]:
        return self._sources[dimension_name][debater_name]

    async def query(
        self,
        action: AllPanelActions,
        dimension_name: DimensionName | None,
        prompt_template: PromptTemplate,
        allow_ai_callback: bool,
        /,
        **kwargs: Any,
    ) -> str:
        kwargs = dict(**kwargs, info=self._debate_info)
        if dimension_name is not None:
            kwargs["dimension"] = self._dimensions[dimension_name]

        cache: list[ChatMessage] = []
        callback_dimension_name: str = sanitize(dimension_name, DimensionName(""))

        for message_template in prompt_template:
            message: ChatMessage = message_template.format(**kwargs)
            cache.append(message)
            await self.callback(message, action=action, dimension_name=callback_dimension_name)

        response: ChatMessage = await self._model.chat_predict(
            messages=ChatHistory(root=tuple(cache))
        )

        cache.append(response)
        if allow_ai_callback or response.role != ChatRole.AI:
            await self.callback(response, action=action, dimension_name=callback_dimension_name)

        return response.content

    async def get_speech_score(self, *, debater_name: DebaterName, judgment: str) -> int:
        return await self._verdict_extractor.get_speech_score(
            self.debate_info, debater_name, judgment, model=self._model, parser=self._parser
        )

    async def get_debater_score_and_judgment(
        self, *, debater_name: DebaterName, judgment: str
    ) -> tuple[int, str]:
        return await self._verdict_extractor.get_debater_score_and_judgment(
            self.debate_info, debater_name, judgment, model=self._model, parser=self._parser
        )

    async def get_winner(self, *, judgment: str) -> DebaterName:
        return await self._verdict_extractor.get_winner(
            self.debate_info, judgment, model=self._model, parser=self._parser
        )

    async def callback(
        self,
        message: ChatMessage | None,
        /,
        *,
        action: AllPanelActions,
        dimension_name: DimensionName,
    ) -> None:
        if self._callback_func is not None:
            await self._callback_func(
                action,
                dimension_name,
                None if message is None else (message.role.value, message.content),
            )

    async def close(self) -> None:
        await self._model.close()


class InterfaceWithHelper(ABC, Generic[T]):
    def __init__(self, *, helper: Helper) -> None:
        super().__init__()
        self._helper = helper
        self._templates: dict[T, PromptTemplate] = {}

    @property
    def helper(self) -> Helper:
        return self._helper

    @property
    @abstractmethod
    def allow_concurrency(self) -> bool:
        raise NotImplementedError()

    @property
    @abstractmethod
    def allow_ai_callback(self) -> bool:
        raise NotImplementedError()

    def set_templates(
        self, templates: Iterable[TemplateInfo[T]], /, *, common_system_prompt: str | None = None
    ) -> None:
        self._templates = {
            template.name: self._add_common_system_prompt(
                template.messages, common_system_prompt=common_system_prompt
            )
            for template in templates
        }

    @staticmethod
    def _add_common_system_prompt(
        template: PromptTemplate, /, *, common_system_prompt: str | None = None
    ) -> PromptTemplate:
        if common_system_prompt is None:
            return template

        return (
            MessageTemplate(
                role=template[0].role,
                content="\n\n".join([common_system_prompt, template[0].content]),
            ),
            *template[1:],
        )
