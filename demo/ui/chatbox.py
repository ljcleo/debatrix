from collections.abc import AsyncIterable, Iterable
from types import EllipsisType
from typing import Literal
from uuid import uuid4

from nicegui import ui

from debatrix.util import sanitize

from .util import get_avatar_url, prettify_json


class ChatMessage:
    def __init__(self, message_ui: ui.chat_message, /, *, render_markdown: bool = True) -> None:
        self._ui = message_ui
        self._render_markdown = render_markdown
        self._contents: list[str] = []
        self._update_last(split=True)

    def append(self, chunk: str | EllipsisType, /) -> None:
        if chunk is ...:
            if len(self._contents) > 0:
                self._update_last()
                self._update_last(split=True)

            self._contents.append("")
        else:
            if len(self._contents) == 0:
                self._contents.append("")

            self._contents[-1] += chunk
            self._update_last()

    def cut(self) -> list[str]:
        if len(self._contents) > 0:
            self._update_last()
        else:
            self._ui.remove(self._last_element)

        return self._contents

    def _update_last(self, *, split: bool = False) -> None:
        if split:
            with self._ui:
                self._last_element = ui.spinner("dots", size="xl", color="black")
        else:
            self._ui.remove(self._last_element)
            content: str = prettify_json(self._contents[-1])

            with self._ui:
                self._last_element = (
                    ui.markdown(content=content)
                    if self._render_markdown
                    else ui.code(content=content, language="markdown")
                ).classes("w-full overflow-x-auto")


class ChatBox:
    SYSTEM_NAME: Literal["[_Host_]"] = "[_Host_]"

    def __init__(
        self, *, title: tuple[str, str | None] | None = None, extra_classes: str | None = None
    ) -> None:
        self._messages: dict[str, ChatMessage] = {}

        classes: str = "w-full h-full"
        if extra_classes is not None:
            classes = " ".join((classes, extra_classes))

        with ui.card().tight().classes(classes) as self._card, ui.column().classes(
            "w-full h-full gap-y-0"
        ):
            if title is not None:
                with ui.card_section().classes("w-full"), ui.row().classes("gap-x-1 items-center"):
                    if title[1] is not None:
                        ui.icon(title[1], size="sm")

                    ui.label(title[0]).classes("text-xl")

            with ui.scroll_area().props(
                'content-style="width: 100%" content-active-style="width: 100%"'
            ).classes("w-full h-auto grow") as self._scroll:
                self._column: ui.column = ui.column().classes("w-full items-stretch")

    def set_visibility(self, visible: bool, /) -> None:
        self._card.set_visibility(visible)

    def reset(self, *, preload: Iterable[str] | None = None) -> None:
        self._messages.clear()
        self._column.clear()

        if preload is not None:
            self.insert(preload, stamp="Preload info")

    def insert(
        self,
        messages: Iterable[str],
        *,
        source: str | None = None,
        stamp: str | None = None,
        bg_color: str | None = None,
        render_markdown: bool = True,
    ) -> list[str]:
        uuid: str = self.assign_message(
            source=source, stamp=stamp, bg_color=bg_color, render_markdown=render_markdown
        )

        for i, chunk in enumerate(messages):
            if i > 0:
                self.append_to_message(uuid, chunk=...)

            self.append_to_message(uuid, chunk=chunk)

        return self.cut_message(uuid)

    async def insert_stream(
        self,
        stream: AsyncIterable[str | EllipsisType],
        *,
        source: str | None = None,
        stamp: str | None = None,
        bg_color: str | None = None,
        render_markdown: bool = True,
    ) -> list[str]:
        uuid: str = self.assign_message(
            source=source, stamp=stamp, bg_color=bg_color, render_markdown=render_markdown
        )

        async for chunk in stream:
            self.append_to_message(uuid, chunk=chunk)

        return self.cut_message(uuid)

    def assign_message(
        self,
        *,
        source: str | None = None,
        stamp: str | None = None,
        bg_color: str | None = None,
        render_markdown: bool = True,
    ) -> str:
        uuid: str = uuid4().hex
        name: str = sanitize(source, self.SYSTEM_NAME)
        avatar: str = get_avatar_url(name)

        with self._column, ui.chat_message(
            name=name, stamp=stamp, avatar=avatar, sent=source is None
        ).props('size="10"') as chat:
            if bg_color is not None:
                chat.props(f'bg-color="{bg_color}"')

            self._messages[uuid] = ChatMessage(chat, render_markdown=render_markdown)

        self._to_bottom()
        return uuid

    def append_to_message(self, uuid: str, /, *, chunk: str | EllipsisType) -> None:
        self._messages[uuid].append(chunk)
        self._to_bottom()

    def cut_message(self, uuid: str, /) -> list[str]:
        return self._messages[uuid].cut()

    def _to_bottom(self) -> None:
        self._scroll.scroll_to(percent=1)
