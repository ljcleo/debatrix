from nicegui import ui

from .base import BaseUI


class HelpUI(BaseUI[[]]):
    def init_ui(self) -> None:
        ui.markdown(
            """## How to use this demo?

1. Enter your OpenAI API key (we will only use it for this demo);
2. Select a preset debate motion;
3. Watch how Debatrix judge the debate with ChatGPT!

## What to do next?

1. Click on the winner verdicts to see the judge's comments;
2. Compare all debaters' scores in the SCORE tab;
3. Click on the score bars and panel score area to see per-debater comments;
4. Click on DETAIL to see how Debatrix analyze speeches;
5. Click on SAVE to download the debate judge record;
6. Select another preset motion and start another debate!

## Can I customize it?

1. Yes! Click on CONFIG to change the settings;
2. Change the backend model to GPT-4 or switch to an ablated framework **(can cost a lot more)**;
3. Change the weights of each dimension, disable some globally or exclude them from
   multi-dimensional summary;
4. **(Advanced)** Design your own prompts! (You might want to read
   [this](https://github.com/ljcleo/Debatrix/blob/main/debatrix/core/common.py),
   [this](https://github.com/ljcleo/Debatrix/blob/main/debatrix/panel/interface/judge/judge.py) and
   [this](https://github.com/ljcleo/Debatrix/blob/main/debatrix/panel/interface/panel/panel.py)
   before your DIY 👻)

## So what is Debatrix after all?

1. It is a LLM-based multi-dimensional debate judge using iterative speech analysis!
2. Find out more on our [Homepage 🏠]()!
3. Or, visit our [GitHub repo 🐈‍⬛](https://github.com/ljcleo/Debatrix)!
4. Or, read our [paper 📃](https://arxiv.org/abs/2403.08010)!
"""
        )
