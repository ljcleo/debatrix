from nicegui import ui

from debatrix.platform import Platform

from ..base import BaseUI
from .arena import ArenaInterfaceConfigUI
from .dimension import DimensionConfigUI
from .model import ModelConfigUI
from .panel import PanelInterfaceConfigUI
from .platform import PlatformConfigUI


class ConfigUI(BaseUI[Platform]):
    def init_ui(self, platform: Platform) -> None:
        with ui.tabs().props("dense").classes("w-full") as config_tabs:
            ui.tab("model", label="Model", icon="smart_toy")
            ui.tab("arena", label="Arena", icon="stadium")
            ui.tab("panel", label="Panel", icon="grading")
            ui.tab("dimension", label="Dimensions", icon="category")
            ui.tab("platform", label="Platform", icon="computer")

        with ui.tab_panels(config_tabs, value="model").classes("w-full grow"):
            with ui.tab_panel("model"):
                ModelConfigUI().register_ui(platform.model_config_data)
            with ui.tab_panel("arena"):
                ArenaInterfaceConfigUI().register_ui(platform.arena_interface_config_data)
            with ui.tab_panel("panel"):
                PanelInterfaceConfigUI().register_ui(platform.panel_interface_config_data)
            with ui.tab_panel("dimension"):
                DimensionConfigUI().register_ui(platform.dimensions_data)
            with ui.tab_panel("platform"):
                PlatformConfigUI().register_ui(platform.platform_config_data)
