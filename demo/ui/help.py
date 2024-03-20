from nicegui import ui

from .base import BaseUI
from ..static import load_img_base64


class HelpUI(BaseUI[[]]):
    def init_ui(self) -> None:
        url_homepage: str = "https://ljcleo.github.io/debatrix"
        url_github: str = "https://github.com/ljcleo/debatrix"
        url_paper: str = "https://arxiv.org/abs/2403.08010"

        with ui.column().classes("w-full items-center"):
            with ui.row().classes("items-center gap-8"):
                ui.avatar(
                    f"img:data:image/png;base64,{load_img_base64('icon.png')}",
                    color="sky-200",
                    size="8rem",
                    font_size="8rem",
                )

                with ui.column().classes("items-center gap-0"):
                    ui.markdown("# Debatrix")

                    with ui.row().classes("items-center"):
                        with ui.link(target=url_homepage, new_tab=True):
                            ui.icon("home", size="lg", color="teal-300").tooltip("Project Homepage")

                        with ui.link(target=url_github, new_tab=True):
                            ui.icon("code", size="lg", color="violet-300").tooltip("GitHub Repo")

                        with ui.link(target=url_paper, new_tab=True):
                            ui.icon("description", size="lg", color="red-300").tooltip("Paper")

            with ui.expansion(group="help", value=True).classes("w-full") as expansion:
                with expansion.add_slot("header"), ui.row().classes("w-full"):
                    ui.label("How to use this demo?").classes("text-3xl")

                ui.markdown(
                    """
1. Enter your OpenAI API key (we will only use it for this demo);
2. Select a preset debate motion;
3. Watch how Debatrix judge the debate with ChatGPT!
"""
                )

            with ui.expansion(group="help").classes("w-full") as expansion:
                with expansion.add_slot("header"), ui.row().classes("w-full"):
                    ui.label("What to do next?").classes("text-3xl")

                ui.markdown(
                    """
1. Click on the winner verdicts to see the judge's comments;
2. Compare all debaters' scores in the SCORE tab;
3. Click on the score bars and panel score area to see per-debater comments;
4. Click on DETAIL to see how Debatrix analyze speeches;
5. Click on SAVE to download the debate judge record;
6. Select another preset motion and start another debate!
"""
                )

            with ui.expansion(group="help").classes("w-full") as expansion:
                with expansion.add_slot("header"), ui.row().classes("w-full"):
                    ui.label("Can I customize it?").classes("text-3xl")

                ui.markdown(
                    """
1. Yes! Click on CONFIG to change the settings;
2. Change the backend model to GPT-4 or switch to an ablated framework **(can cost a lot more)**;
3. Change the weights of each dimension, disable some globally or exclude them from
   multi-dimensional summary;
4. **(Advanced)** Design your own prompts! (You might want to read
   [this](https://github.com/ljcleo/debatrix/blob/main/debatrix/core/common.py),
   [this](https://github.com/ljcleo/debatrix/blob/main/debatrix/panel/interface/judge/judge.py) and
   [this](https://github.com/ljcleo/debatrix/blob/main/debatrix/panel/interface/panel/panel.py)
   before your DIY 👻)
"""
                )

            with ui.expansion(group="help").classes("w-full") as expansion:
                with expansion.add_slot("header"), ui.row().classes("w-full"):
                    ui.label("So what is Debatrix after all?").classes("text-3xl")

                ui.markdown(
                    f"""
1. It is a LLM-based multi-dimensional debate judge using iterative speech analysis!
2. Find out more on our [Homepage 🏠]({url_homepage})!
3. Or, visit our [GitHub repo 🐈‍⬛]({url_github})!
4. Or, read our [paper 📃]({url_paper})!
"""
                )
