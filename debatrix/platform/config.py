from pydantic.dataclasses import dataclass

from ..arena.interface.config import ArenaInterfaceConfig
from ..manager.config import ManagerConfig
from ..model.config import ModelConfig
from ..panel.interface.config import PanelInterfaceConfig
from .record.config import RecorderConfig


@dataclass(kw_only=True)
class Config:
    model: ModelConfig
    arena: ArenaInterfaceConfig
    panel: PanelInterfaceConfig
    manager: ManagerConfig
    recorder: RecorderConfig
