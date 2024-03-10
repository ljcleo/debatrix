import re
from asyncio import sleep
from collections.abc import AsyncIterator
from json import dumps
from random import Random

from ....util import tokenize
from ..base import ChatModelABC
from ...common import ChatHistory, ChatMessage, ChatRole
from .config import TestChatModelConfig


class TestChatModel(ChatModelABC):
    BANK: tuple[str, ...] = tuple(
        (
            "voyage chivalrous fill threatening old-fashioned preserve possessive river quiver "
            "balance mine way lethal adjustment calm yard attempt value key exotic enormous blow "
            "camera nutty rich paint disgusting repeat growth manage quirky macabre things quince "
            "frog cold fold kittens bored reason necessary unbecoming coherent frame vacation "
            "three bite-sized sock range purpose absent needy nappy premium hate flaky excuse "
            "disagreeable insurance magic list humorous tap alcoholic scribble talented mother "
            "skinny huge exclusive rabbit queen scarce double draconian gainful actor loving "
            "riddle last massive bells continue decide joke furry badge flight eminent shoe tail "
            "literate discussion ticket look flag touch bright wail onerous"
        ).split()
    )

    @property
    def config(self) -> TestChatModelConfig:
        return self._config

    @config.setter
    def config(self, config: TestChatModelConfig) -> None:
        self._config = config

    async def predict(self, messages: ChatHistory) -> AsyncIterator[ChatMessage]:
        for token in tokenize(self._respond(messages)):
            await sleep(self.config.streaming_delay)
            yield ChatMessage(role=ChatRole.AI, content=token)

    async def predict_direct(self, messages: ChatHistory) -> ChatMessage:
        await sleep(self.config.direct_delay)
        return ChatMessage(role=ChatRole.AI, content=self._respond(messages))

    def _respond(self, messages: ChatHistory, /) -> str:
        concat_messages: str = ("\n\n" + "-" * 16 + "\n\n").join(
            f"{message.role}:\n\n{message.content}" for message in messages
        )

        debaters: list[str] = []

        for match in re.finditer(
            r"debaters are: (.+(?:, .+)*)$", concat_messages, flags=re.MULTILINE
        ):
            debaters.extend(debater.strip() for debater in match.group(1).strip().split(","))

        def has(pattern: str, /, *, quoted: bool = True) -> bool:
            if quoted:
                pattern = f'"{pattern}"'

            return concat_messages.count(pattern) > 0

        gen = Random(x=hash(concat_messages))

        def ipsum() -> str:
            return " ".join(gen.choices(self.BANK, k=gen.randint(10, 50))) + "\n"

        if has(
            "Above, the Completion did not satisfy the constraints given in the Instructions.",
            quoted=False,
        ):
            print(f"cannot_fix:\n\n{concat_messages}")
            raise RuntimeError(f"cannot_fix: {concat_messages}")

        if has("Score for Specific Debater"):
            return dumps({"score": gen.randint(1, 10)})
        elif has("Judgment and Score for Specific Debater"):
            return dumps({"judgment": ipsum(), "score": gen.randint(1, 10)})
        elif has("Winner of Debate"):
            return dumps({"winner": gen.choice(debaters + ["It's a tie!"])})
        else:
            return ipsum()
