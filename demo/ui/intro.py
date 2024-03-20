from nicegui import app, ui

from debatrix.platform import Session

from .base import BaseUI


class IntroUI(BaseUI[Session, ui.dialog]):
    def init_ui(self, session: Session, dlg_intro: ui.dialog) -> None:
        with ui.column().classes("w-full items-center"):
            temp_data: dict[str, str | None] = dict(api_key="", motion=None)

            async def hdl_btn_start() -> None:
                session.config_data["model"]["chat_config"]["openai_config"]["api_key"] = temp_data[
                    "api_key"
                ]

                dlg_intro.close()
                await session.update_config()
                await session.select_debate(temp_data["motion"])
                await session.reset_debate()
                await session.start_debate()
                app.storage.user["need_intro"] = False

            with ui.stepper().props("vertical").classes("w-full") as stepper:
                with ui.step("Welcome", icon="sentiment_satisfied"):
                    ui.markdown(
                        """### Welcome to Debatrix!

This demo relies on ChatGPT and GPT-4 from OpenAI.

It needs a valid OpenAI API key to show its magic.

Follow the instructions and see how it judge debates!
"""
                    )

                    with ui.stepper_navigation():
                        ui.button("Got it!", on_click=stepper.next, icon="thumb_up")

                with ui.step("Enter OpenAI API Key", icon="key"):
                    ui.label("Please enter your OpenAI API Key:").classes("text-lg")
                    ui.label("(we will only use it for this demo)")

                    ui.input(
                        label="OpenAI API Key",
                        placeholder="sk-XXXXXXXX",
                        password=True,
                        password_toggle_button=True,
                    ).classes("w-full").bind_value_to(temp_data, target_name="api_key")

                    with ui.stepper_navigation():
                        ui.button("Confirm", on_click=stepper.next, icon="done").bind_enabled_from(
                            temp_data, target_name="api_key", backward=lambda x: len(x) > 0
                        )

                        ui.button("Back", on_click=stepper.previous).props("flat")

                with ui.step("Select Debate Motion", icon="topic"):
                    ui.label("Select a preset debate motion and start the debate!").classes(
                        "text-lg"
                    )

                    ui.select(
                        {
                            motion_id: f'<span class="line-clamp-1">{motion}</span>'
                            for motion_id, motion in session.motions
                        },
                        label="Motion",
                        clearable=True,
                    ).props('options-html behavior="dialog"').classes("w-full").bind_value(
                        temp_data, target_name="motion"
                    )

                    with ui.stepper_navigation():
                        ui.button(
                            "Let's go!",
                            on_click=hdl_btn_start,
                            color="positive",
                            icon="play_circle",
                        ).bind_enabled_from(
                            temp_data, target_name="motion", backward=lambda x: x is not None
                        )

                        ui.button("Back", on_click=stepper.previous).props("flat")
