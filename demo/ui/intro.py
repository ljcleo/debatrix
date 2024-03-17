from typing import Any

from nicegui import app, ui
from nicegui.events import ValueChangeEventArguments

from debatrix.platform import Session

from .base import BaseUI


class IntroUI(BaseUI[Session, ui.dialog]):
    def init_ui(self, session: Session, dlg_intro: ui.dialog) -> None:
        openai_config: dict[str, Any] = session.config_data["model"]["chat_config"]["openai_config"]

        with ui.column().classes("w-full"):

            async def reset_motion(e: ValueChangeEventArguments) -> None:
                if len(e.value) == 0:
                    await session.select_debate(None)

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
                ).classes("w-full").bind_value_to(openai_config, target_name="api_key")

            async def hdl_sel_debate(e: ValueChangeEventArguments) -> None:
                await session.select_debate(e.value)

            with ui.card().classes("w-full").bind_visibility_from(
                openai_config, target_name="api_key", backward=lambda x: len(x) > 0
            ):
                ui.label("Step 2: Select a preset debate motion").classes("w-full text-2xl")

                ui.select(
                    {
                        motion_id: f'<span class="line-clamp-1">{motion}</span>'
                        for motion_id, motion in session.motions
                    },
                    label="Motion",
                    on_change=hdl_sel_debate,
                    clearable=True,
                ).props('options-html behavior="dialog"').classes("w-full").bind_value_from(
                    session, target_name="cur_motion"
                )

            async def hdl_btn_start() -> None:
                dlg_intro.close()
                motion: str | None = session.cur_motion
                app.storage.user["need_intro"] = False
                await session.update_config()
                app.storage.user["need_intro"] = True
                await session.select_debate(motion)
                await session.reset_debate()
                await session.start_debate()
                app.storage.user["need_intro"] = False

            with ui.card().classes("w-full items-center").bind_visibility_from(
                session, target_name="is_control_enabled"
            ):
                ui.button("Start the debate!", on_click=hdl_btn_start).classes("text-2xl")
