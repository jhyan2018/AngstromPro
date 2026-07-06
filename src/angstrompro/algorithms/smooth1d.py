# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Smoothing algorithms for 1D/2D UDS (curve stacks).

Registered processes
--------------------
    curve.smooth_savgol
        Savitzky-Golay smoothing — preserves peak positions and heights
        better than a simple moving average.

    curve.smooth_gaussian
        Gaussian (sigma-based) convolution smoothing.
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

# ---------------------------------------------------------------------------
# Shared input spec
# ---------------------------------------------------------------------------

_INPUT = InputSpec(
    name        = "data",
    type_id     = "uds",
    label       = "Curve stack",
    description = "UdsDataStru with ndim=1 (single curve) or ndim=2 (curve stack).",
    ndim        = None,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _apply_rows(data: np.ndarray, fn) -> np.ndarray:
    """Apply fn to each row of a 1D or 2D array, return same shape."""
    if data.ndim == 1:
        return fn(data)
    return np.vstack([fn(row) for row in data])


def _output(src: UdsDataStru, smoothed: np.ndarray, suffix: str) -> UdsDataStru:
    return UdsDataStru(
        name         = src.name + suffix,
        data         = smoothed,
        axes         = copy.deepcopy(src.axes),
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
        landmarks    = copy.deepcopy(src.landmarks),
    )


def _validate(src: UdsDataStru, process_name: str) -> None:
    if src.data.ndim not in (1, 2):
        raise ValueError(
            f"{process_name} requires ndim=1 or ndim=2; got shape {src.data.shape}."
        )


# ---------------------------------------------------------------------------
# curve.smooth_savgol
# ---------------------------------------------------------------------------

@register_process(
    name        = "curve.smooth_savgol",
    label       = "Smooth (Savitzky-Golay)",
    category    = "Curve",
    schema      = ProcessSchema(
        inputs=[_INPUT],
        params=[
            ParameterSpec(
                name        = "window_length",
                type        = int,
                default     = 11,
                label       = "Window length (pts)",
                min         = 3,
                max         = 501,
                step        = 2,
                description = "Number of data points in the smoothing window. Must be odd.",
            ),
            ParameterSpec(
                name        = "polyorder",
                type        = int,
                default     = 3,
                label       = "Polynomial order",
                min         = 1,
                max         = 10,
                description = "Order of the fitting polynomial. Must be < window_length.",
            ),
        ],
    ),
    description = "Savitzky-Golay smoothing for 1D/2D UDS. Preserves peak positions "
                  "and heights better than moving-average smoothing.",
)
def smooth_savgol(inputs: dict, params: dict, *,
                  annotations: dict | None = None) -> UdsDataStru:
    from scipy.signal import savgol_filter

    src: UdsDataStru = inputs["data"]
    _validate(src, "curve.smooth_savgol")

    wl = int(params["window_length"])
    po = int(params["polyorder"])

    # enforce odd window
    if wl % 2 == 0:
        wl += 1
    # enforce polyorder < window_length
    po = min(po, wl - 1)

    smoothed = _apply_rows(src.data.astype(float),
                           lambda row: savgol_filter(row, wl, po))
    return _output(src, smoothed, "_savgol")


# ---------------------------------------------------------------------------
# curve.smooth_gaussian
# ---------------------------------------------------------------------------

@register_process(
    name        = "curve.smooth_gaussian",
    label       = "Smooth (Gaussian)",
    category    = "Curve",
    schema      = ProcessSchema(
        inputs=[_INPUT],
        params=[
            ParameterSpec(
                name        = "sigma",
                type        = float,
                default     = 2.0,
                label       = "Sigma (pts)",
                min         = 0.1,
                max         = 100.0,
                step        = 0.5,
                description = "Standard deviation of the Gaussian kernel in data points.",
            ),
        ],
    ),
    description = "Gaussian convolution smoothing for 1D/2D UDS.",
)
def smooth_gaussian(inputs: dict, params: dict, *,
                    annotations: dict | None = None) -> UdsDataStru:
    from scipy.ndimage import gaussian_filter1d

    src: UdsDataStru = inputs["data"]
    _validate(src, "curve.smooth_gaussian")

    sigma    = float(params["sigma"])
    smoothed = _apply_rows(src.data.astype(float),
                           lambda row: gaussian_filter1d(row, sigma))
    return _output(src, smoothed, "_gauss")
