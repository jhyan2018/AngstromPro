# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Shared UDS → plot-ready entry conversion, used by all plot widgets.
"""
from __future__ import annotations

import re

import numpy as np

from .si_scale import si_scale


def prepare_entry(name: str, uds) -> dict:
    """
    Convert a UdsDataStru into a plot-ready entry dict::

        {
            "uds":     UdsDataStru,
            "x":       np.ndarray  shape (n_pts,)   — SI-scaled x values
            "x_label": str         e.g. "Bias (mV)"
            "y":       np.ndarray  shape (n_curves, n_pts) — SI-scaled y values
            "y_label": str         e.g. "dI/dV (nA/V)"
        }
    """
    data = np.asarray(uds.data, dtype=float)
    if data.ndim == 1:
        y_arr = data[np.newaxis, :]
    elif data.ndim == 2:
        y_arr = data
    else:
        raise ValueError(f"CurveStackViewer expects 1D or 2D data; got {data.ndim}D")

    n_pts = y_arr.shape[-1]
    if uds.axes:
        x_raw  = np.asarray(uds.axes[-1].values, dtype=float)
        ax_obj = uds.axes[-1]
    else:
        x_raw  = np.arange(n_pts, dtype=float)
        ax_obj = None

    # x scaling
    x_prefix, x_scale = si_scale(x_raw) if x_raw.size > 0 else ('', 1.0)
    x_arr = x_raw * x_scale

    if ax_obj is not None:
        x_units = ax_obj.units or ""
        x_label = f"{ax_obj.label} ({x_prefix}{x_units})" if x_units else ax_obj.label
    else:
        x_label = ""

    # y scaling
    y_prefix, y_scale = si_scale(y_arr) if y_arr.size > 0 else ('', 1.0)
    y_arr = y_arr * y_scale

    info    = uds.info if hasattr(uds, "info") and isinstance(uds.info, dict) else {}
    raw_col = info.get("column_name", "") or info.get("Data_Name_Unit", "")
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", raw_col)
    if m:
        y_base_label = info.get("channel_display_name") or m.group(1)
        y_units      = m.group(2)
        y_label      = f"{y_base_label} ({y_prefix}{y_units})"
    else:
        y_base_label = info.get("channel_display_name") or raw_col or name
        y_label      = f"{y_base_label} ({y_prefix})" if y_prefix else y_base_label

    return {"uds": uds, "x": x_arr, "x_label": x_label,
            "y": y_arr, "y_label": y_label}
