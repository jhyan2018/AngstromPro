# -*- coding: utf-8 -*-
"""
Created on Sat Jun 28 2026

@author: jiahaoYan

2D crop algorithm — registered as "spatial.crop2d".

Crops a 2D UdsDataStru along both axes using physical coordinate ranges
(same units as Axis.values). Index arithmetic is done here; callers supply
only physical min/max values.

Registered processes
--------------------
    spatial.crop2d   Crop a 2D map to an (x_min, x_max) × (y_min, y_max) window.
"""

from __future__ import annotations

import copy
import time

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = ProcessSchema(
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "2D Map",
            description = "The 2D UdsDataStru to crop. Must have exactly 2 axes.",
            ndim        = 2,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "x_min",
            type        = float,
            default     = 0.0,
            label       = "X min",
            description = "Lower bound along the first axis (same units as axis values).",
        ),
        ParameterSpec(
            name        = "x_max",
            type        = float,
            default     = 1.0,
            label       = "X max",
            description = "Upper bound along the first axis.",
        ),
        ParameterSpec(
            name        = "y_min",
            type        = float,
            default     = 0.0,
            label       = "Y min",
            description = "Lower bound along the second axis.",
        ),
        ParameterSpec(
            name        = "y_max",
            type        = float,
            default     = 1.0,
            label       = "Y max",
            description = "Upper bound along the second axis.",
        ),
        ParameterSpec(
            name        = "inclusive",
            type        = bool,
            default     = True,
            label       = "Inclusive bounds",
            description = "Include data points exactly at min/max when True.",
        ),
    ],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _axis_slice(axis: Axis, lo: float, hi: float, inclusive: bool) -> slice:
    """Return a slice into axis.values that covers [lo, hi] (or (lo, hi))."""
    v = axis.values
    if inclusive:
        mask = (v >= lo) & (v <= hi)
    else:
        mask = (v > lo) & (v < hi)
    indices = np.where(mask)[0]
    if indices.size == 0:
        raise ValueError(
            f"No data points found between {lo} and {hi} "
            f"(axis range is [{v.min():.4g}, {v.max():.4g}])."
        )
    return slice(int(indices[0]), int(indices[-1]) + 1)


# ---------------------------------------------------------------------------
# Registered process
# ---------------------------------------------------------------------------

@register_process(
    name        = "spatial.crop2d",
    label       = "Crop 2D",
    category    = "Spatial",
    schema      = _SCHEMA,
    description = "Crop a 2D map to an (x_min, x_max) × (y_min, y_max) window.",
)
def crop2d(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    """
    Crop a 2D UdsDataStru to a rectangular region in physical coordinates.

    Parameters (via params dict)
    ----------------------------
    x_min, x_max : float
        Crop window along axis 0.
    y_min, y_max : float
        Crop window along axis 1.
    inclusive : bool
        Whether boundary points are included.

    Returns
    -------
    UdsDataStru
        New object with cropped data and trimmed axes. proc_history is
        appended automatically by ProcessRegistry after this function returns.
    """
    src: UdsDataStru = inputs["data"]

    # Artificial delay so the Task Dashboard can be observed during development.
    # Remove once real STM data processing provides natural runtime.
    time.sleep(30)

    if src.data.ndim != 2:
        raise ValueError(
            f"spatial.crop2d requires a 2D array; got shape {src.data.shape}."
        )
    if len(src.axes) < 2:
        raise ValueError(
            f"spatial.crop2d requires at least 2 axes; got {len(src.axes)}."
        )

    x_min     = params["x_min"]
    x_max     = params["x_max"]
    y_min     = params["y_min"]
    y_max     = params["y_max"]
    inclusive = params["inclusive"]

    if x_min >= x_max:
        raise ValueError(f"x_min ({x_min}) must be less than x_max ({x_max}).")
    if y_min >= y_max:
        raise ValueError(f"y_min ({y_min}) must be less than y_max ({y_max}).")

    sx = _axis_slice(src.axes[0], x_min, x_max, inclusive)
    sy = _axis_slice(src.axes[1], y_min, y_max, inclusive)

    cropped_data = src.data[sx, sy].copy()

    cropped_axes = [
        Axis(
            values = src.axes[0].values[sx].copy(),
            label  = src.axes[0].label,
            units  = src.axes[0].units,
            ticks  = {
                k: v for k, v in src.axes[0].ticks.items()
                if src.axes[0].values[sx][0] <= k <= src.axes[0].values[sx][-1]
            },
        ),
        Axis(
            values = src.axes[1].values[sy].copy(),
            label  = src.axes[1].label,
            units  = src.axes[1].units,
            ticks  = {
                k: v for k, v in src.axes[1].ticks.items()
                if src.axes[1].values[sy][0] <= k <= src.axes[1].values[sy][-1]
            },
        ),
        *[copy.deepcopy(ax) for ax in src.axes[2:]],  # pass through any extra axes
    ]

    return UdsDataStru(
        name         = src.name + "_crop",
        data         = cropped_data,
        axes         = cropped_axes,
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
        landmarks    = {
            k: v for k, v in src.landmarks.items()
            if (cropped_axes[0].values[0]  <= k[0] <= cropped_axes[0].values[-1] and
                cropped_axes[1].values[0]  <= k[1] <= cropped_axes[1].values[-1])
        },
    )
