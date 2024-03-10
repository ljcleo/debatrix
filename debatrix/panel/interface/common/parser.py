import re
from json import JSONDecodeError, dumps, loads
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from pydantic.dataclasses import dataclass

from ....model import ModelClient
from .util import format_jinja2, make_single_chat

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True, kw_only=True)
class ParserConfig:
    schema_prompt_template: str
    fix_prompt_template: str


class JSONParser:
    @property
    def config(self) -> ParserConfig:
        return self._config

    @config.setter
    def config(self, config: ParserConfig) -> None:
        self._config = config

    def make_schema_prompt(self, output_type: type[T], /) -> str:
        return format_jinja2(
            self.config.schema_prompt_template, schema=dumps(output_type.model_json_schema())
        )

    async def parse(
        self,
        raw: str,
        output_type: type[T],
        /,
        *,
        fix_model: ModelClient | None = None,
        max_retries: int = 3,
    ) -> T:
        retries = 0

        while retries <= max_retries:
            try:
                match: re.Match | None = re.search(
                    r"\{.*\}", raw.strip(), re.MULTILINE | re.IGNORECASE | re.DOTALL
                )

                json_str = ""
                if match is not None:
                    json_str = match.group()

                return output_type.model_validate(loads(json_str, strict=False))
            except (JSONDecodeError, ValidationError) as e:
                if fix_model is None or retries == max_retries:
                    raise e
                else:
                    retries += 1

                    raw = (
                        await fix_model.predict_direct(
                            make_single_chat(
                                self.config.fix_prompt_template,
                                instructions=self.make_schema_prompt(output_type),
                                completion=raw,
                                error=repr(e),
                            )
                        )
                    ).content

        raise RuntimeError("Failed to parse")
