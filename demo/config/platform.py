from typing import Any

from nicegui import ui

from ..base import BaseUI


class PlatformConfigUI(BaseUI[dict[str, Any]]):
    def init_ui(self, config: dict[str, Any]) -> None:
        with ui.column().classes("w-full"):
            ui.switch("Should Summarize General Verdict").classes("w-full").bind_value(
                config, "should_summarize"
            )

            ui.switch("Record Prompts").classes("w-full").bind_value(config, "record_prompts")

            ui.switch("Record Verdict Only").classes("w-full").bind_value(
                config, "record_verdict_only"
            )
