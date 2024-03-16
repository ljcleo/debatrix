from typing import Any

from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from debatrix.platform import Session

from ..base import BaseUI
from .util import VALIDATIONS


class ConfigUI(BaseUI[Session]):
    def init_ui(self, session: Session) -> None:
        config: dict[str, Any] = session.config_data

        with ui.expansion("Backend Model", icon="smart_toy", group="config", value=True).classes(
            "w-full"
        ):
            openai_config: dict[str, Any] = config["model"]["chat_config"]["openai_config"]

            ui.select(
                options=["gpt-3.5-turbo-0125", "gpt-4-preview-0125"], label="OpenAI Model"
            ).classes("w-full").bind_value(openai_config, target_name="model")

            ui.input(
                label="OpenAI API Key",
                placeholder="sk-XXXXXXXX",
                password=True,
                password_toggle_button=True,
                validation=VALIDATIONS,
            ).classes("w-full").bind_value(openai_config, target_name="api_key")

        with ui.expansion("Debate Judge", icon="grading", group="config").classes("w-full"):
            judge_config: dict[str, Any] = config["panel"]["judge_config"]

            def toggle_speech_analysis(e: ValueChangeEventArguments) -> None:
                judge_config["iterate_analysis"] &= bool(e.value)

            ui.switch(
                "Analyze Speech for Final Judgment", on_change=toggle_speech_analysis
            ).classes("w-full").bind_value(judge_config, target_name="analyze_speech")

            ui.switch("Iterate Content Analyses Across Speeches").classes("w-full").bind_value(
                judge_config, target_name="iterate_analysis"
            ).bind_enabled_from(judge_config, target_name="analyze_speech")

            action_title: dict[str, str] = {
                "update": "Dimensional Speech Analysis Prompt",
                "judge": "Dimensional Debate Analysis Prompt",
                "summarize": "Multi-dimensional Summary Prompt",
            }

            for template in judge_config["templates"]:
                with ui.expansion(text=action_title[template["name"]], group="prompt").classes(
                    "w-full"
                ):
                    ui.textarea(label="SYSTEM (Dimensional Prefix)").classes("w-full").bind_value(
                        judge_config, "common_system_prompt"
                    )

                    for message in template["messages"]:
                        ui.textarea(label=message["role"].upper()).classes("w-full").bind_value(
                            message, "content"
                        )

            panel_config: dict[str, Any] = config["panel"]["panel_config"]

            for template in panel_config["templates"]:
                with ui.expansion(text=action_title[template["name"]], group="prompt").classes(
                    "w-full"
                ):
                    ui.textarea(label="SYSTEM (Multi-dimensional Prefix)").classes(
                        "w-full"
                    ).bind_value(panel_config, "common_system_prompt")

                    for message in template["messages"]:
                        ui.textarea(label=message["role"].upper()).classes("w-full").bind_value(
                            message, "content"
                        )

        with ui.expansion("Dimensions", icon="category", group="config").classes("w-full"):
            dimensions_config: list[dict[str, Any]] = config["manager"]["dimensions"]

            for dimension in dimensions_config:
                with ui.expansion(dimension["name"].capitalize(), group="dimension").classes(
                    "w-full"
                ):
                    ui.number(
                        label="Weight (-1: disabled; 0: not used in multi-dimensional summary)",
                        min=-1,
                        precision=0,
                        step=1,
                        format="%d",
                    ).classes("w-full").bind_value(dimension, target_name="weight", forward=int)

                    with ui.expansion(text="Prompts").classes("w-full").bind_visibility_from(
                        dimension, target_name="weight", backward=lambda x: x >= 0
                    ):
                        prompt: dict[str, Any] = dimension["prompt"]

                        ui.textarea(label="Judge Whole Debate").classes("w-full").bind_value(
                            prompt, "judge_debate"
                        )

                        ui.textarea(label="Analyze Speech Content").classes("w-full").bind_value(
                            prompt, "analyze_speech"
                        )

                        ui.textarea(label="Use Previous Speech/Analysis").classes(
                            "w-full"
                        ).bind_value(prompt, "use_previous")

                        ui.textarea(label="Judge by Speech Analysis").classes("w-full").bind_value(
                            prompt, "judge_by_analysis"
                        )
