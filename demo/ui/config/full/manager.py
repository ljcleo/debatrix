from typing import Any

from nicegui import ui

from ...base import BaseUI


class ManagerConfigUI(BaseUI[list[Any]]):
    def init_ui(self, config: dict[str, Any]) -> None:
        with ui.grid(columns=1).classes("w-full"):
            ui.switch("Summarize General Verdict").classes("w-full").bind_value(
                config, "should_summarize"
            )

            for dimension in config["dimensions"]:
                with ui.card().classes("w-full"):
                    ui.label(text=dimension["name"].capitalize()).classes("w-full text-lg")

                    with ui.row().classes("w-full items-center"):
                        ui.number(label="Weight", min=-1, precision=0, step=1, format="%d").classes(
                            "grow"
                        ).bind_value(dimension, target_name="weight", forward=int)

                        ui.switch("Allow Tie").bind_value(
                            dimension, target_name="allow_tie"
                        ).bind_enabled_from(
                            dimension, target_name="weight", backward=lambda x: x >= 0
                        )

                    with ui.expansion(text="Prompts").classes("w-full").bind_visibility_from(
                        dimension, target_name="weight", backward=lambda x: x >= 0
                    ):
                        prompt: dict[str, Any] = dimension["prompt"]

                        ui.textarea(label="Judge Whole Debate").props("autogrow").classes(
                            "w-full"
                        ).bind_value(prompt, "judge_debate")

                        ui.textarea(label="Analyze Speech Content").props("autogrow").classes(
                            "w-full"
                        ).bind_value(prompt, "analyze_speech")

                        ui.textarea(label="Use Previous Speech/Analysis").props("autogrow").classes(
                            "w-full"
                        ).bind_value(prompt, "use_previous")

                        ui.textarea(label="Judge by Speech Analysis").props("autogrow").classes(
                            "w-full"
                        ).bind_value(prompt, "judge_by_analysis")
