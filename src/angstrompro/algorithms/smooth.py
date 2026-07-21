# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Smoothing algorithms for curve stacks (1D) and image stacks (2D).

Registered processes
--------------------
    curve.smooth_1d
        Smooth each curve in a ndim=2 UDS (curve stack).
        Method: Gaussian (default) or Savitzky-Golay.

    curve.smooth_2d
        Gaussian spatial smoothing of each layer in a ndim=3 UDS (image stack).
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

# ---------------------------------------------------------------------------
# Implementation helpers
# ---------------------------------------------------------------------------

def _smooth_1d_gaussian(row: np.ndarray, sigma: float) -> np.ndarray:
    from scipy.ndimage import gaussian_filter1d
    return gaussian_filter1d(row.astype(float), sigma)


def _smooth_1d_savgol(row: np.ndarray, window_length: int, polyorder: int) -> np.ndarray:
    from scipy.signal import savgol_filter
    wl = window_length if window_length % 2 == 1 else window_length + 1
    po = min(polyorder, wl - 1)
    return savgol_filter(row.astype(float), wl, po)


def _apply_along_curves(data: np.ndarray, fn) -> np.ndarray:
    """Apply fn to each row (curve) of a ndim=2 array."""
    return np.vstack([fn(data[i]) for i in range(data.shape[0])])


def _output(src: UdsDataStru, smoothed: np.ndarray, suffix: str) -> UdsDataStru:
    return UdsDataStru(
        name         = src.name + suffix,
        data         = smoothed,
        axes         = copy.deepcopy(src.axes),
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
        landmarks    = copy.deepcopy(src.landmarks),
    )


_OUT_2D = [OutputSpec(type_id="uds", ndim=2, label="Curve Stack", description="ndim=2 UDS (curves × points).")]
_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

# ---------------------------------------------------------------------------
# curve.smooth_1d
# ---------------------------------------------------------------------------

@register_process(
    name        = "curve.smooth_1d",
    label       = "Smooth 1D",
    category    = "Filtering & Background",
    schema      = ProcessSchema(
        outputs=_OUT_2D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "Curve Stack",
                description = "UdsDataStru with ndim=2 (curve stack).",
                ndim        = 2,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "method",
                type        = str,
                default     = "Gaussian",
                label       = "Method",
                description = "Smoothing kernel: Gaussian or Savitzky-Golay.",
            ),
            ParameterSpec(
                name        = "sigma",
                type        = float,
                default     = 2.0,
                label       = "Sigma (pts)",
                min         = 0.1,
                max         = 100.0,
                step        = 0.5,
                description = "Standard deviation of the Gaussian kernel in data points. "
                              "Used when method=Gaussian.",
            ),
            ParameterSpec(
                name        = "window_length",
                type        = int,
                default     = 11,
                label       = "Window length (pts)",
                min         = 3,
                max         = 501,
                step        = 2,
                description = "Smoothing window size in data points (must be odd). "
                              "Used when method=Savitzky-Golay.",
            ),
            ParameterSpec(
                name        = "polyorder",
                type        = int,
                default     = 3,
                label       = "Polynomial order",
                min         = 1,
                max         = 10,
                description = "Polynomial order for fitting (must be < window_length). "
                              "Used when method=Savitzky-Golay.",
            ),
        ],
    ),
    description = (
        "Smooth each curve in a ndim=2 (curve stack) UDS along axis[-1]. "
        "method='Gaussian': sigma-based convolution. "
        "method='Savitzky-Golay': polynomial fitting, better preserves peak positions."
    ),
)
def smooth_1d(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 2:
        raise ValueError(f"curve.smooth_1d requires ndim=2; got shape {src.data.shape}.")

    method = str(params.get("method", "Gaussian")).strip()

    if method == "Savitzky-Golay":
        wl = int(params.get("window_length", 11))
        po = int(params.get("polyorder", 3))
        smoothed = _apply_along_curves(src.data, lambda row: _smooth_1d_savgol(row, wl, po))
        suffix = "_savgol"
    elif method == "Gaussian":
        sigma = float(params.get("sigma", 2.0))
        smoothed = _apply_along_curves(src.data, lambda row: _smooth_1d_gaussian(row, sigma))
        suffix = "_gauss"
    else:
        raise ValueError(
            f"curve.smooth_1d: unknown method {method!r}. "
            f"Choose 'Gaussian' or 'Savitzky-Golay'."
        )

    return _output(src, smoothed, suffix)


# ---------------------------------------------------------------------------
# curve.smooth_2d
# ---------------------------------------------------------------------------

@register_process(
    name        = "curve.smooth_2d",
    label       = "Smooth 2D",
    category    = "Filtering & Background",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "Image Stack",
                description = "UdsDataStru with ndim=3 (image stack).",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "sigma",
                type        = float,
                default     = 1.0,
                label       = "Sigma (pts)",
                min         = 0.1,
                max         = 50.0,
                step        = 0.5,
                description = "Standard deviation of the 2D Gaussian kernel in pixels. "
                              "Applied independently to each layer.",
            ),
        ],
    ),
    description = (
        "Gaussian spatial smoothing of each layer in a ndim=3 (image stack) UDS. "
        "Uses a 2D Gaussian kernel applied independently per layer."
    ),
)
def smooth_2d(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    from scipy.ndimage import gaussian_filter

    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"curve.smooth_2d requires ndim=3; got shape {src.data.shape}.")

    sigma = float(params.get("sigma", 1.0))
    data  = src.data.astype(float)
    smoothed = np.stack(
        [gaussian_filter(data[i], sigma=sigma) for i in range(data.shape[0])],
        axis=0,
    )
    return _output(src, smoothed, "_gauss2d")
