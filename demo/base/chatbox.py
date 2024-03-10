from asyncio import Lock, Queue, Task, create_task, sleep
from collections.abc import AsyncIterable, AsyncIterator, Iterable
from types import EllipsisType
from typing import Literal

from nicegui import ui

from debatrix.util import sanitize, tokenize

from ..util import get_avatar_url, prettify_json


class ChatBox:
    SYSTEM_NAME: Literal["[_Host_]"] = "[_Host_]"

    def __init__(
        self, *, title: tuple[str, str | None] | None = None, extra_classes: str | None = None
    ) -> None:
        self._lock = Lock()

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

    @property
    def card(self) -> ui.card:
        return self._card

    @property
    def scroll(self) -> ui.scroll_area:
        return self._scroll

    @property
    def column(self) -> ui.column:
        return self._column

    async def reset(self) -> None:
        async with self._lock:
            self.column.clear()

    async def insert(
        self,
        messages: Iterable[str],
        *,
        source: str | None = None,
        stamp: str | None = None,
        bg_color: str | None = None,
        iter_sleep: float | None = None,
        render_streaming: bool = True,
        render_markdown: bool = True,
    ) -> list[str]:
        async def stream_messages(messages: Iterable[str]) -> AsyncIterator[str | EllipsisType]:
            started: bool = False

            for message in messages:
                if started:
                    yield ...

                started = True

                if iter_sleep is None:
                    yield message
                else:
                    for token in tokenize(message):
                        if iter_sleep is not None and iter_sleep > 0:
                            await sleep(iter_sleep)

                        yield token

        return await self.insert_stream(
            stream_messages(messages),
            source=source,
            stamp=stamp,
            bg_color=bg_color,
            render_streaming=render_streaming,
            render_markdown=render_markdown,
        )

    async def insert_stream(
        self,
        stream: AsyncIterable[str | EllipsisType],
        *,
        source: str | None = None,
        stamp: str | None = None,
        bg_color: str | None = None,
        render_streaming: bool = True,
        render_markdown: bool = True,
    ) -> list[str]:
        name: str = sanitize(source, self.SYSTEM_NAME)

        async with self._lock:
            contents: list[str] = []
            avatar: str = get_avatar_url(name)

            def make_element(content: str | None, /) -> ui.element:
                if content is None:
                    return ui.spinner("dots", size="xl", color="black")
                else:
                    content = prettify_json(content)

                    if render_markdown:
                        return ui.markdown(content=content).classes("w-full overflow-x-auto")
                    else:
                        return ui.code(content=content, language="markdown").classes(
                            "w-full overflow-x-auto"
                        )

            with self.column, ui.chat_message(
                name=name, stamp=stamp, avatar=avatar, sent=source is None
            ).props('size="10"') as chat:
                last_block: ui.element = make_element(None)

            self.scroll.scroll_to(percent=1)
            if bg_color is not None:
                chat.props(f'bg-color="{bg_color}"')

            async for chunk in stream:
                if chunk is ...:
                    if len(contents) > 0:
                        chat.remove(last_block)

                        with chat:
                            make_element(contents[-1])
                            last_block = make_element(None)

                        self.scroll.scroll_to(percent=1)

                    contents.append("")
                else:
                    if len(contents) == 0:
                        contents.append("")

                    contents[-1] += chunk

                    if render_streaming:
                        chat.remove(last_block)
                        with chat:
                            last_block = make_element(contents[-1])

                        self.scroll.scroll_to(percent=1)

            chat.remove(last_block)

            if len(contents) > 0:
                with chat:
                    make_element(contents[-1])

            return contents


class DelayedChatBox(ChatBox):
    def __init__(
        self, *, title: tuple[str, str | None] | None = None, extra_classes: str | None = None
    ) -> None:
        super().__init__(title=title, extra_classes=extra_classes)
        self._task: Task[Iterable[str]] | None = None

    async def reset(self, preload: Iterable[str] | None = None) -> None:
        if self._task is not None:
            await self.cancel()

        await super().reset()
        if preload is not None:
            await self.insert(preload, stamp="Preload info", render_streaming=False)

    async def start(
        self,
        *,
        source: str | None = None,
        stamp: str | None = None,
        bg_color: str | None = None,
        render_streaming: bool = True,
        render_markdown: bool = True,
    ) -> bool:
        if self._task is not None:
            return False

        self._cache: Queue[str | EllipsisType | None] = Queue()

        async def get_messages() -> AsyncIterator[str | EllipsisType]:
            while True:
                messages: str | EllipsisType | None = await self._cache.get()
                if messages is None:
                    return

                yield messages

        self._task = create_task(
            self.insert_stream(
                get_messages(),
                source=source,
                stamp=stamp,
                bg_color=bg_color,
                render_streaming=render_streaming,
                render_markdown=render_markdown,
            )
        )

        return True

    def update(self, chunk: str | EllipsisType, /) -> bool:
        if self._task is None:
            return False

        self._cache.put_nowait(chunk)
        return True

    async def stop(self) -> bool:
        if self._task is None:
            return False

        self._cache.put_nowait(None)
        await self._task
        self._task = None
        return True

    async def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await sleep(0)
            self._task = None
