from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from ....model import ChatHistory, ChatMessage, ChatRole


def format_jinja2(template: str, /, **kwargs) -> str:
    return SandboxedEnvironment(undefined=StrictUndefined).from_string(template).render(**kwargs)


def make_single_chat(template: str, /, **kwargs) -> ChatHistory:
    return ChatHistory(
        root=(ChatMessage(role=ChatRole.HUMAN, content=format_jinja2(template, **kwargs)),)
    )
