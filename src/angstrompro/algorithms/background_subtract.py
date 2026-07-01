# -*- coding: utf-8 -*-
"""
Background subtraction processes for AngstromPro.

Registered processes
--------------------
    spatial.bg_subtract
        Subtract a polynomial background from every layer of a 3-D stack.
        Two methods:

        2DPlane   — fit an n-th order 2-D polynomial surface to the whole
                    layer (least-squares) and subtract it.  Mean value of
                    the original layer is preserved.

        PerLine   — fit and subtract a 1-D polynomial to each row
                    independently, then remove each row's residual mean.
                    Mean value of the original layer is preserved.
"""

from __future__ import annotations

import copy
import itertools

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

# ---------------------------------------------------------------------------
# Core algorithms (ported from BackgroundSubtract.py)
# ---------------------------------------------------------------------------

def _bg_subtract_2d_plane(data2D: np.ndarray, order: int) -> np.ndarray:
    """Fit and subtract an n-th order 2-D polynomial surface (least squares).

    Coordinates are normalised to [-1, 1] before fitting to keep the design
    matrix well-conditioned at higher orders (raw pixel indices 0…N-1 raise
    to high powers produce values ~N^order that make lstsq numerically unstable).
    """
    rows, cols = data2D.shape
    X, Y = np.meshgrid(np.arange(cols), np.arange(rows))
    # Normalise to [-1, 1]
    Xn = 2.0 * X / (cols - 1) - 1.0
    Yn = 2.0 * Y / (rows - 1) - 1.0
    xv = Xn.ravel()
    yv = Yn.ravel()
    zv = data2D.ravel()

    terms = [(i, j) for i, j in itertools.product(range(order + 1), range(order + 1))
             if i + j <= order]
    A = np.column_stack([(xv ** i) * (yv ** j) for i, j in terms])
    p, *_ = np.linalg.lstsq(A, zv, rcond=None)

    Z_bg = sum(p[k] * (Xn ** i) * (Yn ** j) for k, (i, j) in enumerate(terms))
    return data2D - Z_bg + np.mean(data2D)


def _bg_subtract_per_line(data2D: np.ndarray, order: int) -> np.ndarray:
    """Fit and subtract a 1-D polynomial row-by-row, then remove row mean.

    Column coordinates are normalised to [-1, 1] for numerical stability.
    """
    rows, cols = data2D.shape
    mean_orig = np.mean(data2D)
    out = np.empty_like(data2D, dtype=np.float64)

    # Normalised column coordinate, shared across all rows
    Yn = 2.0 * np.arange(cols) / (cols - 1) - 1.0   # [-1, 1]

    # 1-D polynomial terms in Yn only (per-line fit ignores row position)
    terms_1d = list(range(order + 1))
    A = np.column_stack([Yn ** j for j in terms_1d])

    for r in range(rows):
        p, *_ = np.linalg.lstsq(A, data2D[r], rcond=None)
        bg = sum(p[j] * Yn ** j for j in terms_1d)
        row_sub = data2D[r] - bg
        out[r] = row_sub - np.mean(row_sub)

    return out + mean_orig


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = ProcessSchema(
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "3D Stack",
            description = "UdsDataStru with ndim=3 (layers × rows × cols).",
            ndim        = 3,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "method",
            type        = str,
            default     = "2DPlane",
            label       = "Method",
            description = "2DPlane: fit a 2-D polynomial surface per layer. "
                          "PerLine: fit a 1-D polynomial to each row.",
            choices     = ["2DPlane", "PerLine"],
        ),
        ParameterSpec(
            name        = "order",
            type        = int,
            default     = 1,
            label       = "Polynomial order",
            description = "Order of the polynomial background to remove "
                          "(1 = linear/plane, 2 = quadratic, …).",
            min         = 1,
            max         = 6,
            step        = 1,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Registered process
# ---------------------------------------------------------------------------

@register_process(
    name        = "spatial.bg_subtract",
    label       = "Background Subtract",
    category    = "Spatial",
    schema      = _SCHEMA,
    description = "Subtract a polynomial background from every layer of a 3-D stack.",
)
def bg_subtract(inputs: dict, params: dict,
                *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(
            f"spatial.bg_subtract requires ndim=3; got {src.data.shape}.")

    method: str = params["method"]
    order: int  = int(params["order"])

    out = np.empty_like(src.data, dtype=np.float64)
    for i in range(src.data.shape[0]):
        if method == "2DPlane":
            out[i] = _bg_subtract_2d_plane(src.data[i], order)
        elif method == "PerLine":
            out[i] = _bg_subtract_per_line(src.data[i], order)
        else:
            raise ValueError(f"Unknown background subtraction method: {method!r}")

    return UdsDataStru(
        name         = src.name + "_bg",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
