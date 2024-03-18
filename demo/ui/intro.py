from nicegui import app, ui
from nicegui.events import ValueChangeEventArguments

from debatrix.platform import Session

from .base import BaseUI


class IntroUI(BaseUI[Session, ui.dialog]):
    def init_ui(self, session: Session, dlg_intro: ui.dialog) -> None:
        with ui.column().classes("w-full items-center"):
            temp_data: dict[str, str | None] = dict(api_key="", motion=None)

            def reset_motion(e: ValueChangeEventArguments) -> None:
                temp_data["api_key"] = e.value
                if len(e.value) == 0:
                    temp_data["motion"] = None

            with ui.card().classes("w-full"):
                ui.label("Step 1: Enter your OpenAI API key").classes("w-full text-2xl")

                ui.label("(we will only use it for this demo)").classes(
                    "w-full font-bold text-right"
                )

                ui.input(
                    label="OpenAI API Key",
                    placeholder="sk-XXXXXXXX",
                    password=True,
                    password_toggle_button=True,
                    on_change=reset_motion,
                ).classes("w-full")

            with ui.card().classes("w-full").bind_visibility_from(
                temp_data, target_name="api_key", backward=lambda x: len(x) > 0
            ):
                ui.label("Step 2: Select a preset debate motion").classes("w-full text-2xl")

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

            ui.button(
                "Start!", on_click=hdl_btn_start, color="positive", icon="play_circle"
            ).classes("text-xl").bind_visibility_from(
                temp_data, target_name="motion", backward=lambda x: x is not None
            )
