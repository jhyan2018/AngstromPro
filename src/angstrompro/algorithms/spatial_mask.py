# -*- coding: utf-8 -*-
"""
Spatial window (apodization) process for AngstromPro.

Multiplies every layer of a real-space 3-D stack by a 2-D window function
centred at the mask_center annotation point.  Useful for isolating a region
of interest before further analysis (e.g. FFT).

Registered processes
--------------------
    spatial.mask2d
        Multiply each layer by a 2-D window centred at the mask_center
        annotation (a single picked point).  Name suffix: _msk.
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
from angstrompro.core.processes.param_schema import AnnotationSpec

# ---------------------------------------------------------------------------
# Window functions
# ---------------------------------------------------------------------------

def _gaussian_window(n_rows: int, n_cols: int,
                     center_row: float, center_col: float,
                     sigma: float) -> np.ndarray:
    R, C = np.ogrid[:n_rows, :n_cols]
    return np.exp(-((R - center_row) ** 2 + (C - center_col) ** 2) / (2 * sigma ** 2))


def _hann_window(n_rows: int, n_cols: int, **_) -> np.ndarray:
    return np.outer(np.hanning(n_rows), np.hanning(n_cols))


def _hamming_window(n_rows: int, n_cols: int, **_) -> np.ndarray:
    return np.outer(np.hamming(n_rows), np.hamming(n_cols))


def _blackman_window(n_rows: int, n_cols: int, **_) -> np.ndarray:
    return np.outer(np.blackman(n_rows), np.blackman(n_cols))


_WINDOW_FN = {
    "gaussian": _gaussian_window,
    "hann":     _hann_window,
    "hamming":  _hamming_window,
    "blackman": _blackman_window,
}

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

_SCHEMA = ProcessSchema(
    outputs=_OUT_3D,
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "3D Stack",
            description = "Real-space UdsDataStru with ndim=3 (layers × rows × cols).",
            ndim        = 3,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "window",
            type        = str,
            default     = "gaussian",
            label       = "Window type",
            description = "Shape of the apodization window.",
            choices     = ["gaussian", "hann", "hamming", "blackman"],
        ),
        ParameterSpec(
            name        = "sigma",
            type        = float,
            default     = 10.0,
            label       = "Sigma (Gaussian only)",
            description = "Standard deviation of the Gaussian window (pixels). "
                          "Ignored for other window types.",
            min         = 0.1,
        ),
    ],
    annotations=[
        AnnotationSpec(
            name     = "mask_center",
            role     = "mask_center",
            type_id  = "point_set",
            required = True,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Registered process
# ---------------------------------------------------------------------------

@register_process(
    name        = "spatial.mask_2d",
    label       = "Spatial Window Mask 2D",
    category    = "Spatial",
    schema      = _SCHEMA,
    description = "Multiply each layer of a real-space 3-D stack by a 2-D apodization window "
                  "centred at the mask_center annotation point.",
)
def mask2d(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"spatial.mask_2d requires ndim=3; got shape {src.data.shape}.")

    if not annotations or "mask_center" not in annotations:
        raise ValueError(
            "spatial.mask_2d requires a 'mask_center' annotation. "
            "Use Points → 'Set Mask Center from Main' to define it first."
        )

    center_pt = annotations["mask_center"]
    if center_pt.coords.shape[0] == 0:
        raise ValueError("mask_center annotation contains no points.")
    center_row = float(center_pt.coords[0, 0])
    center_col = float(center_pt.coords[0, 1])

    n_rows, n_cols = src.data.shape[1], src.data.shape[2]
    fn   = _WINDOW_FN[params["window"]]
    mask = fn(n_rows, n_cols, center_row=center_row, center_col=center_col,
              sigma=params["sigma"])
    out  = src.data * mask[np.newaxis, :, :]

    return UdsDataStru(
        name         = src.name + "_msk",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
