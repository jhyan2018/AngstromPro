from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import WorkspaceData
from .uds_data import UdsDataStru


@dataclass
class PlotStyle:
    color: str      = ""        # empty = auto-assigned by canvas
    linewidth: float = 1.5
    marker: str     = ""        # e.g. "o", "s", "" = no marker
    alpha: float    = 1.0
    label: str      = ""        # curve legend label
    visible: bool   = True


@dataclass
class CanvasConfig:
    title: str          = ""
    x_label: str        = ""
    y_label: str        = ""
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None
    legend_visible: bool = True


@dataclass
class SceneEntry:
    data: UdsDataStru
    style: PlotStyle = field(default_factory=PlotStyle)


@dataclass
class DataScene(WorkspaceData):
    """Multi-curve canvas: several UdsDataStru objects with their plot styles."""
    type_id: ClassVar[str] = "scene"

    name: str
    entries: list[SceneEntry]   = field(default_factory=list)
    canvas_config: CanvasConfig = field(default_factory=CanvasConfig)
