# -*- coding: utf-8 -*-
"""
Created on Mon Jun 22 23:50:31 2026

@author: jiahaoYan
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

import numpy as np

from .base import WorkspaceData, ProcRecord
from .isocontour_data import IsocontourResult


FFT_DOMAIN_KEY = "_angstrompro.data_domain"
FFT_TRANSFORM_KEY = "_angstrompro.transform"
FFT_SOURCE_NAME_KEY = "_angstrompro.source_name"
FFT_WINDOW_KEY = "_angstrompro.fft_window"
FFT_TUKEY_ALPHA_KEY = "_angstrompro.fft_tukey_alpha"

_INTERNAL_INFO_KEY_MIGRATIONS = {
    "angstrompro.data_domain": FFT_DOMAIN_KEY,
    "angstrompro.transform": FFT_TRANSFORM_KEY,
    "angstrompro.source_name": FFT_SOURCE_NAME_KEY,
    "angstrompro.fft_window": FFT_WINDOW_KEY,
    "angstrompro.fft_tukey_alpha": FFT_TUKEY_ALPHA_KEY,
    "source_format": "_source_format",
    "channels": "_channels",
    "column_names": "_column_names",
    "channel_index": "_channel_index",
    "n_points": "_n_points",
    "x_pixels": "_x_pixels",
    "y_pixels": "_y_pixels",
}


def display_info_items(info: dict) -> list[tuple[str, object]]:
    """Return experimental metadata suitable for normal user-facing views.

    By convention, metadata keys beginning with ``_`` are internal.
    """
    visible = []
    for key, value in (info or {}).items():
        text = str(key).strip()
        if text.startswith("_"):
            continue
        visible.append((text, value))
    return visible


def _legacy_fft_source_name(name: str) -> str | None:
    """Resolve legacy ``name_fft`` and deduplicated ``name_fft_2`` forms."""
    if name.endswith("_fft"):
        return name[:-4]
    base, separator, suffix = name.rpartition("_")
    if separator and suffix.isdigit() and base.endswith("_fft"):
        return base[:-4]
    return None


def is_fft_uds(data: "UdsDataStru") -> bool:
    """Return whether *data* is FFT output, with legacy name fallback."""
    info = getattr(data, "info", {}) or {}
    if info.get(FFT_TRANSFORM_KEY) == "fft_2d":
        return True
    if info.get(FFT_DOMAIN_KEY) == "reciprocal":
        return True
    return _legacy_fft_source_name(str(getattr(data, "name", ""))) is not None


def fft_source_name(data: "UdsDataStru") -> str | None:
    """Return the originating real-space name when it is known."""
    info = getattr(data, "info", {}) or {}
    source = str(info.get(FFT_SOURCE_NAME_KEY, "")).strip()
    if source:
        return source
    name = str(getattr(data, "name", ""))
    return _legacy_fft_source_name(name)


class AxisType(Enum):
    SPATIAL_X  = "spatial_x"
    SPATIAL_Y  = "spatial_y"
    SPATIAL_Z  = "spatial_z"
    BIAS       = "bias"
    ENERGY     = "energy"
    FIELD      = "field"
    FREQUENCY  = "frequency"
    TIME       = "time"
    INDEX      = "index"      # generic integer index, no physical meaning
    UNKNOWN    = "unknown"    # physical meaning exists but not yet identified


@dataclass
class Axis:
    values: np.ndarray          # exact float64 array — no precision loss
    label: str = "? (?)"        # e.g. "Bias (V)"
    units: str = ""             # e.g. "V"
    axis_type: AxisType = AxisType.UNKNOWN
    ticks: dict[float, str] = field(default_factory=dict)
    # named positions on this axis, e.g. {0.0: "Γ", 1.23: "X", 2.45: "M"}
    # used for band structure high-symmetry points, phase labels, etc.



@dataclass
class UdsDataStru(WorkspaceData):
    type_id: ClassVar[str] = "uds"

    name:         str                          = ""
    data: np.ndarray                          = field(default_factory=lambda: np.array([]))
    axes: list[Axis]                          = field(default_factory=list)
    info: dict                                = field(default_factory=dict)
    landmarks:   dict[tuple[float, ...], str]  = field(default_factory=dict)
    isocontours: list[IsocontourResult]        = field(default_factory=list)
    proc_history: list[ProcRecord]             = field(default_factory=list)
    # named points in N-dimensional data space, e.g.:
    # 1D k-path  — handled by Axis.ticks
    # 2D BZ map  — {(0.0, 0.0): "Γ", (0.5, 0.5): "K", (1.0, 0.0): "M"}

    def __post_init__(self) -> None:
        """Normalize legacy bookkeeping metadata to the internal-key convention."""
        self.info = dict(self.info or {})
        for old_key, new_key in _INTERNAL_INFO_KEY_MIGRATIONS.items():
            if old_key not in self.info:
                continue
            if new_key not in self.info:
                self.info[new_key] = self.info[old_key]
            del self.info[old_key]

        # Layer position is represented by axes[0]; these keys are obsolete.
        self.info.pop("LayerValue", None)
        self.info.pop("layer_value", None)

    def display_type(self) -> str:
        ndim = self.data.ndim
        kind = {2: "Curve Stack", 3: "Image Stack"}.get(ndim, f"{ndim}D Array")
        return kind

    def summary(self) -> dict[str, str]:
        shape_str = " × ".join(str(s) for s in self.data.shape)
        axes_str  = ", ".join(ax.label for ax in self.axes) if self.axes else "—"
        d = {
            "Name":  self.name,
            "Shape": shape_str,
            "dtype": str(self.data.dtype),
            "Axes":  axes_str,
        }
        if self.proc_history:
            d["History"] = f"{len(self.proc_history)} step(s)"
        return d

    def inspect_fields(self) -> list:
        nodes = []

        # main data array
        nodes.append({"kind": "array", "label": "data", "array": self.data,
                       "children": [
                           {"kind": "value", "label": "shape", "value": str(self.data.shape)},
                           {"kind": "value", "label": "dtype", "value": str(self.data.dtype)},
                           {"kind": "value", "label": "ndim",  "value": str(self.data.ndim)},
                       ]})

        # axes
        ax_children = []
        for i, ax in enumerate(self.axes):
            rng = (f"{ax.values[0]:.4g} … {ax.values[-1]:.4g}"
                   if len(ax.values) > 0 else "empty")
            summary = f"{len(ax.values)} pts   {rng}  {ax.units}"
            ax_children.append({
                "kind": "axis",
                "label": f"[{i}]  [{ax.axis_type.value}]  {ax.label}",
                "summary": summary,
                "axis": ax,
                "children": [
                    {"kind": "value", "label": "axis_type", "value": ax.axis_type.value},
                    {"kind": "array", "label": "values", "array": ax.values},
                    *([{"kind": "group", "label": "ticks",
                        "summary": str(len(ax.ticks)),
                        "children": [{"kind": "value", "label": f"{pos:.4g}", "value": lbl}
                                     for pos, lbl in ax.ticks.items()]}]
                      if ax.ticks else []),
                ],
            })
        nodes.append({"kind": "group", "label": "axes",
                      "summary": f"{len(self.axes)} axis/axes",
                      "children": ax_children})

        # The Inspector is the complete technical view, including internal and
        # structural metadata. Compact module views may apply presentation
        # filtering separately.
        nodes.append({"kind": "group", "label": "info",
                      "summary": f"{len(self.info)} entries",
                      "children": [{"kind": "value", "label": str(k), "value": str(v)}
                                   for k, v in self.info.items()]})

        # proc_history
        ph_children = []
        for i, rec in enumerate(self.proc_history):
            ch = [{"kind": "value", "label": str(k), "value": str(v)}
                  for k, v in rec.params.items()]
            if rec.input_item_names:
                ch.append({"kind": "value", "label": "inputs",
                           "value": ", ".join(rec.input_item_names)})
            ph_children.append({"kind": "group", "label": f"[{i}]",
                                 "summary": rec.step, "children": ch})
        nodes.append({"kind": "group", "label": "proc_history",
                      "summary": f"{len(self.proc_history)} steps",
                      "children": ph_children})

        # isocontours
        if self.isocontours:
            iso_children = []
            for i, r in enumerate(self.isocontours):
                ch = [
                    {"kind": "value", "label": "kind",        "value": r.kind},
                    {"kind": "value", "label": "level",       "value": str(r.level)},
                    {"kind": "value", "label": "method",      "value": r.method},
                    {"kind": "value", "label": "layer_index", "value": str(r.layer_index)},
                    {"kind": "value", "label": "source_axes", "value": str(r.source_axes)},
                ]
                from angstrompro.core.data.isocontour_data import (
                    IsopointResult, IsolineResult, IsosurfaceResult)
                if isinstance(r, IsopointResult):
                    ch.append({"kind": "array", "label": "points", "array": r.points,
                               "children": [{"kind": "value", "label": "count",
                                             "value": str(len(r.points))}]})
                elif isinstance(r, IsolineResult):
                    loop_children = [
                        {"kind": "array", "label": f"[{j}]", "array": c,
                         "children": [{"kind": "value", "label": "points",
                                       "value": str(len(c))}]}
                        for j, c in enumerate(r.contours)
                    ]
                    ch.append({"kind": "group", "label": "contours",
                               "summary": f"{len(r.contours)} loop(s)",
                               "children": loop_children})
                elif isinstance(r, IsosurfaceResult):
                    ch.append({"kind": "value", "label": "vertices",
                               "value": str(r.vertices.shape)})
                    ch.append({"kind": "value", "label": "faces",
                               "value": str(r.faces.shape)})
                if r.notes:
                    ch.append({"kind": "value", "label": "notes", "value": r.notes})
                label = f"[{i}]  {r.kind}  layer={r.layer_index}  level={r.level:g}"
                iso_children.append({"kind": "group", "label": label,
                                     "summary": r.kind, "children": ch})
            nodes.append({"kind": "group", "label": "isocontours",
                          "summary": f"{len(self.isocontours)} result(s)",
                          "children": iso_children})

        # landmarks
        if self.landmarks:
            lm_children = []
            for coords, lbl in self.landmarks.items():
                key = "(" + ", ".join(f"{c:.4g}" for c in coords) + ")"
                lm_children.append({"kind": "value", "label": key, "value": lbl})
            nodes.append({"kind": "group", "label": "landmarks",
                          "summary": f"{len(self.landmarks)} points",
                          "children": lm_children})

        return nodes

    @staticmethod
    def from_array(data: np.ndarray, name: str) -> "UdsDataStru":
        """Legacy fallback: create from raw array with UNKNOWN axes."""
        axes = [
            Axis(values=np.arange(data.shape[i], dtype=float),
                 axis_type=AxisType.UNKNOWN)
            for i in range(data.ndim)
        ]
        return UdsDataStru(name=name, data=np.copy(data), axes=axes)

