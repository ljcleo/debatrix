from collections.abc import Callable

from pydantic.dataclasses import dataclass

from ...common import ANone
from ...core.common import DebaterName

StreamingCallback = Callable[[DebaterName, str | None], ANone]


@dataclass(frozen=True, kw_only=True)
class SpeechData:
    debater_name: DebaterName
    content: str
