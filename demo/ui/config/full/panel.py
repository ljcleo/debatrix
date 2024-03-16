from operator import not_
from typing import Any

from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from ...base import BaseUI


class PanelInterfaceConfigUI(BaseUI[dict[str, Any]]):
    def init_ui(self, config: dict[str, Any]) -> None:
        with ui.grid(columns=1).classes("w-full"):
            with ui.card().classes("w-full"):
                judge_config: Any = config["judge_config"]
                ui.label(text="Judge").classes("w-full text-lg")

                def toggle_judge_concurrency(e: ValueChangeEventArguments) -> None:
                    judge_config["allow_ai_callback"] &= not bool(e.value)

                ui.switch("Enable Concurrency", on_change=toggle_judge_concurrency).classes(
                    "w-full"
                ).bind_value(judge_config, target_name="allow_concurrency")

                ui.switch("Record Raw AI Output").classes("w-full").bind_value(
                    judge_config, target_name="allow_ai_callback"
                ).bind_enabled_from(judge_config, target_name="allow_concurrency", backward=not_)

                ui.switch("Skip Speech Judgement").classes("w-full").bind_value(
                    judge_config, target_name="skip_speech_judgement"
                )

                def toggle_speech_analysis(e: ValueChangeEventArguments) -> None:
                    judge_config["iterate_analysis"] &= bool(e.value)

                ui.switch("Analyze Speeches", on_change=toggle_speech_analysis).classes(
                    "w-full"
                ).bind_value(judge_config, target_name="analyze_speech")

                ui.switch("Iterate Analyses Across Speeches").classes("w-full").bind_value(
                    judge_config, target_name="iterate_analysis"
                ).bind_enabled_from(judge_config, target_name="analyze_speech")

                with ui.expansion(text="Common System Prompt").classes("w-full"):
                    ui.textarea(label="Common System Prompt").props("autogrow").classes(
                        "w-full"
                    ).bind_value(judge_config, "common_system_prompt")

                for template in judge_config["templates"]:
                    with ui.expansion(
                        text=" ".join([template["name"].capitalize(), "Prompt"])
                    ).classes("w-full"):
                        for message in template["messages"]:
                            ui.textarea(label=message["role"].capitalize()).props(
                                "autogrow"
                            ).classes("w-full").bind_value(message, "content")

            with ui.card().classes("w-full"):
                panel_config: Any = config["panel_config"]
                ui.label(text="Panel").classes("w-full text-lg")

                def toggle_panel_concurrency(e: ValueChangeEventArguments) -> None:
                    panel_config["allow_ai_callback"] &= not bool(e.value)

                ui.switch("Enable Concurrency", on_change=toggle_panel_concurrency).classes(
                    "w-full"
                ).bind_value(panel_config, target_name="allow_concurrency")

                ui.switch("Record Raw AI Output").classes("w-full").bind_value(
                    panel_config, target_name="allow_ai_callback"
                ).bind_enabled_from(panel_config, target_name="allow_concurrency", backward=not_)

                with ui.expansion(text="Common System Prompt").classes("w-full"):
                    ui.textarea(label="Common System Prompt").props("autogrow").classes(
                        "w-full"
                    ).bind_value(panel_config, "common_system_prompt")

                for template in panel_config["templates"]:
                    with ui.expansion(
                        text=" ".join([template["name"].capitalize(), "Prompt"])
                    ).classes("w-full"):
                        for message in template["messages"]:
                            ui.textarea(label=message["role"].capitalize()).props(
                                "autogrow"
                            ).classes("w-full").bind_value(message, "content")
