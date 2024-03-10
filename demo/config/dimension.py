from typing import Any

from nicegui import ui

from ..base import BaseUI


class DimensionConfigUI(BaseUI[list[Any]]):
    def init_ui(self, dimensions: list[Any]) -> None:
        with ui.grid(columns=1).classes("w-full"):
            for dimension in dimensions:
                with ui.card().classes("w-full"):
                    ui.label(text=dimension["name"].capitalize()).classes("w-full text-lg")

                    ui.number(label="Weight", min=-1, precision=0, step=1, format="%d").classes(
                        "w-full"
                    ).bind_value(dimension, target_name="weight", forward=int)

                    with ui.card().classes("w-full").bind_visibility_from(
                        dimension, target_name="weight", backward=lambda x: x >= 0
                    ):
                        ui.switch("Allow Tie").classes("w-full").bind_value(
                            dimension, target_name="allow_tie"
                        )

                        with ui.expansion(text="Prompts").classes("w-full"):
                            prompt: dict[str, Any] = dimension["prompt"]

                            ui.textarea(label="Judge Whole Debate").props("autogrow").classes(
                                "w-full"
                            ).bind_value(prompt, "judge_debate")

                            ui.textarea(label="Analyze Speech Content").props("autogrow").classes(
                                "w-full"
                            ).bind_value(prompt, "analyze_speech")

                            ui.textarea(label="Use Previous Speech/Analysis").props(
                                "autogrow"
                            ).classes("w-full").bind_value(prompt, "use_previous")

                            ui.textarea(label="Judge by Speech Analysis").props("autogrow").classes(
                                "w-full"
                            ).bind_value(prompt, "judge_by_analysis")
