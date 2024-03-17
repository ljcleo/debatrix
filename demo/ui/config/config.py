from dataclasses import dataclass
from typing import Any

from nicegui import ui

from debatrix.platform import Session

from ..base import BaseUI
from .full import FullConfigUI
from .util import VALIDATIONS


@dataclass(kw_only=True)
class ConfigUI(BaseUI[Session]):
    enable_full: bool

    def __post_init__(self) -> None:
        super().__init__()
        self._full = FullConfigUI()

    def init_ui(self, session: Session) -> None:
        if self.enable_full:
            self._full.register_ui(session)
            return

        config: dict[str, Any] = session.config_data

        with ui.expansion("Backend Model", icon="smart_toy", group="config", value=True).classes(
            "w-full"
        ):
            openai_config: dict[str, Any] = config["model"]["chat_config"]["openai_config"]

            ui.select(
                options=["gpt-3.5-turbo-0125", "gpt-4-0125-preview"], label="OpenAI Model"
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

            with ui.select(
                options=["gpt", "non_iter", "debatrix"],
                value=(
                    "gpt"
                    if not judge_config["analyze_speech"]
                    else "debatrix" if judge_config["iterate_analysis"] else "non_iter"
                ),
            ).classes("w-full").bind_value_to(
                judge_config, target_name="analyze_speech", forward=lambda x: x != "gpt"
            ).bind_value_to(
                judge_config, target_name="iterate_analysis", forward=lambda x: x == "debatrix"
            ):
                with ui.tooltip():
                    ui.markdown(
                        """- `gpt`: No speech analysis for debate judgment
- `non_iter`: Provide raw previous speeches instead of their analyses for new speech analysis
- `debatrix`: Iterative speech analysis with previous analyses
"""
                    )

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
