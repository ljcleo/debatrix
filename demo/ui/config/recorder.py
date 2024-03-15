from typing import Any

from nicegui import ui

from ..base import BaseUI


class RecorderConfigUI(BaseUI[dict[str, Any]]):
    def init_ui(self, config: dict[str, Any]) -> None:
        with ui.column().classes("w-full"):
            ui.switch("Verdict Only").classes("w-full").bind_value(config, "verdict_only")
            ui.switch("Include Prompts").classes("w-full").bind_value(config, "include_prompts")
