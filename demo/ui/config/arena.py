from typing import Any

from nicegui import ui

from ..base import BaseUI


class ArenaInterfaceConfigUI(BaseUI[dict[str, Any]]):
    def init_ui(self, config: dict[str, Any]) -> None:
        with ui.column().classes("w-full"):
            ui.number(label="Streaming Delay", min=0, step=0.01).classes("w-full").bind_value(
                config, "streaming_delay"
            )

            ui.number(label="Streaming Chunk Size", min=1).classes("w-full").bind_value(
                config, "streaming_chunk_size"
            )
