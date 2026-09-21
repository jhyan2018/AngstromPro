# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Shared UDS → plot-ready entry conversion, used by all plot widgets.
"""
from __future__ import annotations

import numpy as np

from .si_scale import scaled_axis_label, split_label_unit


def prepare_entry(name: str, uds) -> dict:
    """
    Convert a UdsDataStru into a plot-ready entry dict::

        {
            "uds":     UdsDataStru,
            "x":       np.ndarray  shape (n_pts,)   — raw x values
            "x_label": str         e.g. "Bias (V)"
            "y":       np.ndarray  shape (n_curves, n_pts) — raw y values
            "y_label": str         e.g. "dI/dV (A/V)"
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
    x_arr = x_raw

    if ax_obj is not None:
        x_base_label, x_units = split_label_unit(ax_obj.label, ax_obj.units)
        x_label = scaled_axis_label(x_base_label, x_units, 1.0)
    else:
        x_base_label = ""
        x_units = ""
        x_label = ""

    info    = uds.info if hasattr(uds, "info") and isinstance(uds.info, dict) else {}
    raw_col = (info.get("column_name", "")
               or info.get("Data_Name_Unit", "")
               or info.get("channel_loaded", "")
               or info.get("experiment_parameter_loaded", ""))
    raw_base_label, y_units = split_label_unit(
        raw_col, info.get("parameter_units", ""))
    # A dataset/file name identifies the plotted artist; it is not a physical
    # quantity and must never become the Y-axis label.  Leave the label blank
    # when channel metadata is unavailable.
    display_label = info.get("channel_display_name") or ""
    if display_label:
        y_base_label, display_units = split_label_unit(display_label, y_units)
        y_units = y_units or display_units
    else:
        y_base_label = raw_base_label
    y_label = scaled_axis_label(y_base_label, y_units, 1.0)

    # row axis — present when data is 2D and has a non-sweep leading axis
    row_values: np.ndarray | None = None
    row_label: str = ""
    if y_arr.shape[0] > 1 and len(uds.axes) >= 2:
        raw_row = np.asarray(uds.axes[0].values, dtype=float)
        if raw_row.size == y_arr.shape[0]:
            row_values = raw_row
            row_base_label, row_units = split_label_unit(
                uds.axes[0].label, uds.axes[0].units)
            row_label = scaled_axis_label(row_base_label, row_units, 1.0)
        else:
            row_base_label = ""
            row_units = ""
    else:
        row_base_label = ""
        row_units = ""

    return {"uds": uds, "x": x_arr, "x_label": x_label,
            "x_label_base": x_base_label, "x_units": x_units,
            "y": y_arr, "y_label": y_label,
            "y_label_base": y_base_label, "y_units": y_units,
            "row_values": row_values, "row_label": row_label,
            "row_label_base": row_base_label, "row_units": row_units,
            "x_scale": 1.0, "y_scale": 1.0}


def prepare_y_error(error_uds, target_entry: dict) -> np.ndarray:
    """Validate and scale a symmetric Y-error UDS for a plotted dataset.

    Error magnitudes must match the target's normalized ``(curves, points)``
    shape.  Curve values and errors both remain in the UDS' original units;
    the plot axis owns any visible scientific-notation exponent.
    """
    raw = np.asarray(error_uds.data)
    if np.iscomplexobj(raw):
        if np.any(np.imag(raw) != 0):
            raise ValueError("Y-error data must be real-valued.")
        raw = np.real(raw)
    raw = np.asarray(raw, dtype=float)
    if raw.ndim == 1:
        errors = raw[np.newaxis, :]
    elif raw.ndim == 2:
        errors = raw
    else:
        raise ValueError(
            f"Y-error data must be 1-D or 2-D; got {raw.ndim}-D.")

    expected = tuple(np.asarray(target_entry["y"]).shape)
    if tuple(errors.shape) != expected:
        raise ValueError(
            "Y-error shape must match the plotted data: "
            f"expected {expected}, got {tuple(errors.shape)}.")
    if not np.all(np.isfinite(errors)):
        raise ValueError("Y-error data must contain only finite values.")
    if np.any(errors < 0):
        raise ValueError("Y-error magnitudes cannot be negative.")

    target_uds = target_entry.get("uds")
    target_axes = getattr(target_uds, "axes", None) or []
    error_axes = getattr(error_uds, "axes", None) or []
    if target_axes and error_axes:
        target_axis = target_axes[-1]
        error_axis = error_axes[-1]
        target_x = np.asarray(target_axis.values, dtype=float)
        error_x = np.asarray(error_axis.values, dtype=float)
        if target_x.shape != error_x.shape or not np.allclose(
                target_x, error_x, rtol=1e-9, atol=1e-12, equal_nan=True):
            raise ValueError(
                "Y-error sweep-axis values must match the plotted data.")
        target_units = str(getattr(target_axis, "units", "") or "")
        error_units = str(getattr(error_axis, "units", "") or "")
        if target_units and error_units and target_units != error_units:
            raise ValueError(
                "Y-error sweep-axis units must match the plotted data.")

    return errors
