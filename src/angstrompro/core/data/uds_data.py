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

from .base import WorkspaceData


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
class ProcRecord:
    step: str                          # process name, e.g. "crop.1d"
    params: dict      = field(default_factory=dict)   # exact params used
    input_item_names: list[str] = field(default_factory=list)
    # WorkspaceItem names of every input fed to this step, in schema order
    annotations: dict = field(default_factory=dict)
    # role → serialized annotation snapshot (plain dicts, JSON-safe)
    # populated by registry._record_history via serialize_annotation()


@dataclass
class UdsDataStru(WorkspaceData):
    type_id: ClassVar[str] = "uds"

    name: str
    data: np.ndarray
    axes: list[Axis]                          = field(default_factory=list)
    info: dict                                = field(default_factory=dict)
    proc_history: list[ProcRecord]            = field(default_factory=list)
    landmarks: dict[tuple[float, ...], str]   = field(default_factory=dict)
    # named points in N-dimensional data space, e.g.:
    # 1D k-path  — handled by Axis.ticks
    # 2D BZ map  — {(0.0, 0.0): "Γ", (0.5, 0.5): "K", (1.0, 0.0): "M"}

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

        # info
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

