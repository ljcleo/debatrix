from nicegui import ui

from debatrix.platform import Session

from ...base import BaseUI
from .arena import ArenaInterfaceConfigUI
from .manager import ManagerConfigUI
from .model import ModelConfigUI
from .panel import PanelInterfaceConfigUI
from .recorder import RecorderConfigUI


class FullConfigUI(BaseUI[Session]):
    def init_ui(self, session: Session) -> None:
        with ui.tabs().props("dense").classes("w-full") as config_tabs:
            ui.tab("model", label="Model", icon="smart_toy")
            ui.tab("arena", label="Arena", icon="stadium")
            ui.tab("panel", label="Panel", icon="grading")
            ui.tab("manager", label="Manager", icon="category")
            ui.tab("recorder", label="Recorder", icon="computer")

        with ui.tab_panels(config_tabs, value="model").classes("w-full grow"):
            with ui.tab_panel("model"):
                ModelConfigUI().register_ui(session.config_data["model"])
            with ui.tab_panel("arena"):
                ArenaInterfaceConfigUI().register_ui(session.config_data["arena"])
            with ui.tab_panel("panel"):
                PanelInterfaceConfigUI().register_ui(session.config_data["panel"])
            with ui.tab_panel("manager"):
                ManagerConfigUI().register_ui(session.config_data["manager"])
            with ui.tab_panel("recorder"):
                RecorderConfigUI().register_ui(session.config_data["recorder"])
