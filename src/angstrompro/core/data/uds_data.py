# -*- coding: utf-8 -*-
"""
Created on Mon Jun 22 23:50:31 2026

@author: jiahaoYan
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

import numpy as np

from .base import WorkspaceData


@dataclass
class Axis:
    values: np.ndarray          # exact float64 array — no precision loss
    label: str = "? (?)"        # e.g. "Bias (V)"
    units: str = ""             # e.g. "V"
    ticks: dict[float, str] = field(default_factory=dict)
    # named positions on this axis, e.g. {0.0: "Γ", 1.23: "X", 2.45: "M"}
    # used for band structure high-symmetry points, phase labels, etc.


@dataclass
class ProcRecord:
    step: str                          # process name, e.g. "crop.1d"
    params: dict      = field(default_factory=dict)   # exact params used
    input_item_names: list[str] = field(default_factory=list)
    # WorkspaceItem names of every input fed to this step, in schema order


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

    @staticmethod
    def from_array(data: np.ndarray, name: str) -> "UdsDataStru":
        """Create with default pixel-index axes, matching old UdsDataStru.__init__."""
        axes = [
            Axis(values=np.arange(data.shape[i], dtype=float))
            for i in range(data.ndim)
        ]
        #info?
        
        return UdsDataStru(name=name, data=np.copy(data), axes=axes)

