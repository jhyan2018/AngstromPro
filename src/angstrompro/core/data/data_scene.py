from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import WorkspaceData
from .uds_data import UdsDataStru


@dataclass
class PlotStyle:
    color: str       = ""        # empty = auto-assigned by canvas
    linewidth: float = 1.5
    linestyle: str   = "solid"   # "solid", "dashed", "dotted", "dashdot"
    marker: str      = ""        # e.g. "o", "s", "" = no marker
    alpha: float     = 1.0
    label: str       = ""        # curve legend label
    visible: bool    = True


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
    # curve-stack specific
    plot_mode: str   = "stack"    # "stack" | "colormap"
    offset: float    = 0.0        # waterfall offset (stack mode)
    colormap: str    = "RdBu_r"   # colormap name (colormap mode)
    show_grid: bool  = False


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

    def display_type(self) -> str:
        return "Plot Scene"

    def summary(self) -> dict[str, str]:
        d: dict[str, str] = {
            "Name":   self.name,
            "Curves": str(len(self.entries)),
        }
        if self.canvas_config.title:
            d["Title"] = self.canvas_config.title
        if self.canvas_config.x_label:
            d["X"] = self.canvas_config.x_label
        if self.canvas_config.y_label:
            d["Y"] = self.canvas_config.y_label
        return d

    def inspect_fields(self) -> list:
        cfg = self.canvas_config
        cfg_children = [
            {"kind": "value", "label": attr, "value": str(val)}
            for attr, val in [
                ("title",          cfg.title or "—"),
                ("x_label",        cfg.x_label or "—"),
                ("y_label",        cfg.y_label or "—"),
                ("plot_mode",      cfg.plot_mode),
                ("offset",         str(cfg.offset)),
                ("colormap",       cfg.colormap),
                ("show_grid",      str(cfg.show_grid)),
                ("legend_visible", str(cfg.legend_visible)),
                ("x_range",        f"{cfg.x_min} … {cfg.x_max}"),
                ("y_range",        f"{cfg.y_min} … {cfg.y_max}"),
            ]
        ]

        entry_children = []
        for i, entry in enumerate(self.entries):
            uds = entry.data
            style = entry.style
            shape_str = str(uds.data.shape) if uds.data is not None else "—"
            ch = []
            if uds.data is not None:
                ch.append({"kind": "array", "label": "data", "array": uds.data})
            for j, ax in enumerate(uds.axes):
                rng = (f"{ax.values[0]:.4g} … {ax.values[-1]:.4g}"
                       if len(ax.values) > 0 else "empty")
                ch.append({
                    "kind": "group",
                    "label": f"axis[{j}]  {ax.label}",
                    "summary": f"{len(ax.values)} pts  {rng}  {ax.units}",
                    "children": [
                        {"kind": "array", "label": "values", "array": ax.values},
                    ],
                })
            ch.append({
                "kind": "group", "label": "style", "summary": "",
                "children": [
                    {"kind": "value", "label": sattr,
                     "value": str(getattr(style, sattr))}
                    for sattr in ("color", "linewidth", "linestyle",
                                  "marker", "alpha", "label", "visible")
                ],
            })
            entry_children.append({
                "kind": "group",
                "label": f"[{i}]  {uds.name}",
                "summary": shape_str,
                "children": ch,
            })

        return [
            {"kind": "group", "label": "canvas_config",
             "summary": f"mode={cfg.plot_mode}", "children": cfg_children},
            {"kind": "group", "label": "entries",
             "summary": f"{len(self.entries)} curve(s)", "children": entry_children},
        ]
