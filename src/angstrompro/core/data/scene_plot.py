# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

ScenePlot — full hierarchical scene data model.

Hierarchy:
    ScenePlot
    └── figure: FigureConfig
        └── axes_list: list[AxesSpec]
            ├── config: AxesConfig
            ├── extra:  dict          (widget-specific: color_mode, offset, …)
            └── artists: list[ArtistSpec]   (discriminated union on `kind`)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import WorkspaceData, ProcRecord
from .uds_data import UdsDataStru


# ── Artist style dataclasses ──────────────────────────────────────────────────

@dataclass
class LineStyle:
    color:      str         = ""
    linewidth:  float | None = None
    linestyle:  str         = ""
    marker:     str         = ""
    markersize: float | None = None
    step_where: str         = ""    # "" = ax.plot; "pre"|"post"|"mid" = ax.step


@dataclass
class ScatterStyle:
    color:      str         = ""
    cmap:       str         = "viridis"
    vmin:       float | None = None
    vmax:       float | None = None
    s:          float | None = None
    marker:     str         = "o"
    edgecolors: str         = ""


@dataclass
class ImageStyle:
    render:        str         = "pcolormesh"  # "imshow" | "pcolormesh"
    cmap:          str         = "viridis"
    vmin:          float | None = None
    vmax:          float | None = None
    aspect:        str         = "auto"
    interpolation: str         = "nearest"     # imshow only
    origin:        str         = "upper"       # imshow only
    symmetric:     bool        = False         # auto vmin = -vmax


@dataclass
class ContourStyle:
    filled:     bool         = False
    levels:     int          = 10
    cmap:       str          = "viridis"
    colors:     str          = ""
    linewidths: float | None = None
    symmetric:  bool         = False


@dataclass
class FillStyle:
    x_col:      int  = 0
    y1_col:     int  = 1
    y2_col:     int  = 2
    horizontal: bool = False
    facecolor:  str  = ""
    edgecolor:  str  = ""
    hatch:      str  = ""


@dataclass
class BarStyle:
    x_col:      int         = 0
    y_col:      int         = 1
    horizontal: bool        = False
    color:      str         = ""
    edgecolor:  str         = ""
    width:      float | None = None


@dataclass
class ErrorBarStyle:
    x_col:         int         = 0
    y_col:         int         = 1
    yerr_col:      int | None  = None
    xerr_col:      int | None  = None
    yerr_data:     UdsDataStru | None = None   # separate UDS for y-errors
    xerr_data:     UdsDataStru | None = None   # separate UDS for x-errors
    yerr_data_col: int         = 0
    xerr_data_col: int         = 0
    color:         str         = ""
    linewidth:     float | None = None
    capsize:       float | None = None
    ecolor:        str         = ""
    marker:        str         = "o"
    markersize:    float | None = None


@dataclass
class TextStyle:
    x:        float      = 0.0
    y:        float      = 0.0
    s:        str        = ""
    fontsize: float | None = None
    color:    str        = ""
    ha:       str        = "left"
    va:       str        = "bottom"
    rotation: float      = 0.0
    bbox:     dict       = field(default_factory=dict)
    xy_arrow: tuple | None = None   # None = ax.text; set = ax.annotate


@dataclass
class PatchStyle:
    patch_type: str         = "rectangle"  # "rectangle"|"circle"|"ellipse"|"arrow"
    x:          float       = 0.0
    y:          float       = 0.0
    facecolor:  str         = ""
    edgecolor:  str         = ""
    linewidth:  float | None = None
    hatch:      str         = ""
    extra:      dict        = field(default_factory=dict)  # patch-type geometry


# ── ArtistSpec — discriminated union ─────────────────────────────────────────

@dataclass
class ArtistSpec:
    """One matplotlib artist on an axes.

    `kind` is the discriminator: "line"|"scatter"|"image"|"contour"|
    "fill"|"bar"|"errorbar"|"text"|"patch".

    `data` is None for annotation artists (text, patch) that carry no UDS.
    `row` is only meaningful for "line": None = all rows of a 2-D UDS,
    int = single row slice — avoids exploding 120-row UDS into 120 entries.
    """
    kind:    str
    style:   (LineStyle | ScatterStyle | ImageStyle | ContourStyle |
               FillStyle | BarStyle | ErrorBarStyle | TextStyle | PatchStyle)
    data:    UdsDataStru | None = None
    label:   str                = ""
    visible: bool               = True
    zorder:  int | None         = None
    alpha:   float | None       = None
    # line / scatter column selectors
    row:     int | None         = None   # None = all rows
    x_col:   int                = 0
    # overflow for artist-specific params not covered by style dataclasses
    # e.g. row_visibility: list[bool] for multi-row line artists
    extra:   dict               = field(default_factory=dict)


# ── AxesConfig — shared axes settings ────────────────────────────────────────

@dataclass
class AxesConfig:
    title:      str          = ""
    xlabel:     str          = ""
    ylabel:     str          = ""
    xlim:       tuple | None = None
    ylim:       tuple | None = None
    xscale:     str          = "linear"   # "linear"|"log"|"symlog"|"logit"
    yscale:     str          = "linear"
    # None = "never touched" → the rcParams delta (axes.grid / grid.*) rules;
    # an explicit bool (user touched the axes panel) overrides it per-axes
    grid:       bool | None  = None
    grid_which: str          = "major"    # "major"|"minor"|"both"
    legend:     bool         = False
    legend_loc: str          = "best"
    aspect:     str          = "auto"
    # twin-axis secondary labels / limits (populated when twin_axis is set)
    x2label:    str          = ""
    y2label:    str          = ""
    x2lim:      tuple | None = None
    y2lim:      tuple | None = None
    x2scale:    str          = "linear"
    y2scale:    str          = "linear"


# ── AxesSpec ──────────────────────────────────────────────────────────────────

@dataclass
class AxesSpec:
    """One Axes on the figure, plus all artists drawn on it.

    Widget-specific parameters (color_mode, offset, colormap, symmetric)
    live in `extra` to avoid bleeding into shared dataclasses.

    Twin axes: set twin_of = index of parent AxesSpec, twin_axis = "x" or "y".
    Colorbar:  set colorbar_target = index of the axes whose mappable to use.
    """
    config:          AxesConfig       = field(default_factory=AxesConfig)
    artists:         list[ArtistSpec] = field(default_factory=list)
    row:             int              = 0
    col:             int              = 0
    rowspan:         int              = 1
    colspan:         int              = 1
    projection:      str              = "rectilinear"
    twin_of:         int              = -1   # -1 = not a twin
    twin_axis:       str              = ""   # "x" | "y" | ""
    colorbar_target: int              = -1   # -1 = no colorbar
    extra:           dict             = field(default_factory=dict)


# ── FigureConfig ──────────────────────────────────────────────────────────────

@dataclass
class FigureConfig:
    """Subplot layout for a single Figure."""
    nrows:     int               = 1
    ncols:     int               = 1
    mosaic:    str               = ""     # "AB\nCC" — overrides nrows/ncols
    sharex:    bool              = False
    sharey:    bool              = False
    hspace:    float | None      = None
    wspace:    float | None      = None
    suptitle:  str               = ""
    axes_list: list[AxesSpec]    = field(default_factory=list)


# ── ScenePlot ─────────────────────────────────────────────────────────────────

@dataclass
class ScenePlot(WorkspaceData):
    """Complete matplotlib scene: layout + all artists + style snapshot."""
    type_id: ClassVar[str] = "scene_plot"

    name:           str               = ""
    figure:         FigureConfig      = field(default_factory=FigureConfig)
    rcparams_delta: dict              = field(default_factory=dict)
    proc_history:   list[ProcRecord]  = field(default_factory=list)

    def display_type(self) -> str:
        return "Plot Scene"

    def summary(self) -> dict[str, str]:
        axes_list = self.figure.axes_list
        n_artists = sum(len(ax.artists) for ax in axes_list)
        d: dict[str, str] = {
            "Name":    self.name,
            "Axes":    str(len(axes_list)),
            "Artists": str(n_artists),
        }
        if self.figure.suptitle:
            d["Title"] = self.figure.suptitle
        return d

    def inspect_fields(self) -> list:
        fig = self.figure
        fig_children = [
            {"kind": "value", "label": k, "value": str(v)}
            for k, v in [
                ("nrows",    fig.nrows),
                ("ncols",    fig.ncols),
                ("mosaic",   fig.mosaic or "—"),
                ("sharex",   fig.sharex),
                ("sharey",   fig.sharey),
                ("suptitle", fig.suptitle or "—"),
            ]
        ]

        axes_children = []
        for ai, ax_spec in enumerate(fig.axes_list):
            cfg = ax_spec.config
            cfg_items = [
                {"kind": "value", "label": k, "value": str(v)}
                for k, v in [
                    ("title",      cfg.title or "—"),
                    ("xlabel",     cfg.xlabel or "—"),
                    ("ylabel",     cfg.ylabel or "—"),
                    ("xlim",       str(cfg.xlim)),
                    ("ylim",       str(cfg.ylim)),
                    ("xscale",     cfg.xscale),
                    ("yscale",     cfg.yscale),
                    ("grid",       cfg.grid),
                    ("legend",     cfg.legend),
                    ("projection", ax_spec.projection),
                    ("extra",      str(ax_spec.extra)),
                ]
            ]
            artist_items = [
                {"kind": "value",
                 "label": f"[{j}] {a.kind}",
                 "value": a.label or (a.data.name if a.data else "—")}
                for j, a in enumerate(ax_spec.artists)
            ]
            axes_children.append({
                "kind": "group",
                "label": f"axes[{ai}]",
                "summary": f"{len(ax_spec.artists)} artist(s)",
                "children": cfg_items + artist_items,
            })

        return [
            {"kind": "group", "label": "figure",
             "summary": f"{fig.nrows}×{fig.ncols}", "children": fig_children},
            {"kind": "group", "label": "axes",
             "summary": f"{len(fig.axes_list)} axes", "children": axes_children},
        ]
