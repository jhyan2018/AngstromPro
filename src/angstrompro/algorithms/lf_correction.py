# -*- coding: utf-8 -*-
"""
Lattice-distortion Field (LF) correction processes for AngstromPro.

Two registered processes:

    spatial.lf_displacement_field
        Uses two Bragg peaks from the FFT to compute the displacement field
        (ux, uy) via 2-D lock-in demodulation at each peak.  Returns a
        2-layer UDS (layer 0 = ux, layer 1 = uy).

    spatial.lf_correction
        Applies a pre-computed displacement field to every layer of a 3-D
        stack using bilinear pixel interpolation.

Physics
-------
For two Bragg wave-vectors Q1, Q2 the phase maps φ1(r), φ2(r) satisfy:

    φ_i(r) = -Q_i · u(r)

Inverting the 2×2 system gives the displacement field u(r) = (ux, uy).
Each layer is then re-sampled at (X - ux, Y - uy) to correct the distortion.
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
from .lock_in import _lock_in_layer, _unwrap_phase
from .pixel_interpolation import PixelInterpolation


# ── shared helper ─────────────────────────────────────────────────────────────

def _lattice_constant_px(coords: np.ndarray, N: int) -> float:
    """Longest real-space lattice constant (px) from all Bragg peak coordinates."""
    O_k = (N - N % 2) / 2
    best = 0.0
    for pt in coords:
        row, col = float(pt[0]), float(pt[1])
        d = np.sqrt((col - O_k) ** 2 + (row - O_k) ** 2)
        if d > 0:
            best = max(best, N / d)
    return best


def _r_sigma(coords: np.ndarray, N: int, rSigma_ref_a0: float) -> float:
    return rSigma_ref_a0 * _lattice_constant_px(coords, N)


def _compute_displacement_field(data2d: np.ndarray,
                                bPx1: float, bPy1: float,
                                bPx2: float, bPy2: float,
                                r_sigma: float,
                                phase_unwrap: bool,
                                unwrap_method: str = "auto") -> np.ndarray:
    """Return displacement field array shape (2, N, N): [ux, uy]."""
    N = data2d.shape[-1]

    A1 = _lock_in_layer(data2d, bPx1, bPy1, r_sigma)
    phase1 = np.arctan2(np.imag(A1), np.real(A1))
    if phase_unwrap:
        phase1 = _unwrap_phase(phase1, unwrap_method)

    A2 = _lock_in_layer(data2d, bPx2, bPy2, r_sigma)
    phase2 = np.arctan2(np.imag(A2), np.real(A2))
    if phase_unwrap:
        phase2 = _unwrap_phase(phase2, unwrap_method)

    O_k   = (N - N % 2) / 2
    bQ1x  = 2 * np.pi * (bPx1 - O_k) / N
    bQ1y  = 2 * np.pi * (bPy1 - O_k) / N
    bQ2x  = 2 * np.pi * (bPx2 - O_k) / N
    bQ2y  = 2 * np.pi * (bPy2 - O_k) / N

    Q_M     = np.array([[bQ1x, bQ1y], [bQ2x, bQ2y]])
    Q_M_inv = np.linalg.inv(Q_M)

    ux = Q_M_inv[0, 0] * (-phase1) + Q_M_inv[0, 1] * (-phase2)
    uy = Q_M_inv[1, 0] * (-phase1) + Q_M_inv[1, 1] * (-phase2)

    df = np.empty((2, N, N), dtype=np.float64)
    df[0] = np.real(ux)
    df[1] = np.real(uy)
    return df


_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

# ── spatial.lf_displacement_field ─────────────────────────────────────────────

_SCHEMA_DF = ProcessSchema(
    outputs=_OUT_3D,
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "Real-space 3D stack",
            description = "ndim=3 real-space image stack with a 'bragg_peaks' "
                          "annotation carrying at least 2 points (Q1 and Q2).",
            ndim        = 3,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "rSigma_ref_a0",
            type        = float,
            default     = 0.5,
            label       = "σ / a₀",
            description = "Lock-in Gaussian filter width as fraction of lattice constant.",
            min         = 0.01,
            max         = 1000.0,
        ),
        ParameterSpec(
            name        = "phase_unwrap",
            type        = bool,
            default     = True,
            label       = "Phase unwrap",
            description = "Apply reliability-guided 2-D phase unwrapping.",
        ),
        ParameterSpec(
            name        = "unwrap_method",
            type        = str,
            default     = "auto",
            label       = "Unwrap method",
            description = "auto: try skimage then fall back to Python; "
                          "skimage: force skimage (must be installed); "
                          "python: built-in reliability-guided implementation.",
            choices     = ["auto", "skimage", "python"],
        ),
    ],
    annotations=[
        AnnotationSpec(
            name     = "bragg_peaks",
            role     = "bragg_peaks",
            type_id  = "point_set",
            required = True,
        ),
    ],
)


@register_process(
    name        = "spatial.lf_displacement_field_2d",
    label       = "LF Displacement Field 2D",
    category    = "Spatial",
    schema      = _SCHEMA_DF,
    description = "Compute the lattice-distortion displacement field (ux, uy) "
                  "from two Bragg peaks via 2-D lock-in demodulation. "
                  "Returns a 2-layer UDS (layer 0 = ux, layer 1 = uy).",
)
def lf_displacement_field(inputs: dict, params: dict,
                          *, annotations: dict | None = None) -> UdsDataStru:
    src    = inputs["data"]
    coords = (annotations or {}).get("bragg_peaks")
    if coords is None or not hasattr(coords, "coords"):
        raise ValueError("spatial.lf_displacement_field_2d requires a 'bragg_peaks' annotation.")

    pts = coords.coords   # (N, 2) [row, col]
    if pts.shape[0] < 2:
        raise ValueError(
            "spatial.lf_displacement_field_2d requires at least 2 Bragg peaks "
            f"(Q1 and Q2); got {pts.shape[0]}.")

    N        = src.data.shape[-1]
    bPx1, bPy1 = float(pts[0, 1]), float(pts[0, 0])   # col, row
    bPx2, bPy2 = float(pts[1, 1]), float(pts[1, 0])

    rs = _r_sigma(pts, N, params["rSigma_ref_a0"])
    df = _compute_displacement_field(
        src.data[0], bPx1, bPy1, bPx2, bPy2, rs,
        params["phase_unwrap"], params["unwrap_method"],
    )

    ax = copy.deepcopy(src.axes)
    ax[0].values = np.array([0.0, 1.0])   # two layers: ux=0, uy=1

    return UdsDataStru(
        name         = src.name + "_df",
        data         = df,
        axes         = ax,
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )


# ── spatial.lf_correction ─────────────────────────────────────────────────────

_SCHEMA_LF = ProcessSchema(
    outputs=_OUT_3D,
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "Real-space 3D stack",
            description = "ndim=3 stack to be corrected (any channel: topo, dI/dV, etc.).",
            ndim        = 3,
        ),
        InputSpec(
            name        = "displacement_field",
            type_id     = "uds",
            label       = "Displacement field",
            description = "2-layer UDS produced by spatial.lf_displacement_field on the "
                          "topographic channel (layer 0 = ux, layer 1 = uy).",
            ndim        = 3,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "interpolate_method",
            type        = str,
            default     = "bilinear",
            label       = "Interpolation",
            description = "Pixel interpolation method.",
            choices     = ["bilinear"],
        ),
        ParameterSpec(
            name        = "pad_method",
            type        = str,
            default     = "constant",
            label       = "Padding",
            description = "Edge padding mode passed to numpy.pad.",
            choices     = ["constant", "reflect", "edge", "wrap", "symmetric"],
        ),
    ],
    annotations=[],
)


@register_process(
    name        = "spatial.lf_correction_2d",
    label       = "LF Correction 2D",
    category    = "Spatial",
    schema      = _SCHEMA_LF,
    description = "Apply a pre-computed lattice-distortion displacement field to every "
                  "layer of a 3-D stack. Run spatial.lf_displacement_field on the "
                  "topographic channel first to produce the displacement field.",
)
def lf_correction(inputs: dict, params: dict,
                  *, annotations: dict | None = None) -> UdsDataStru:
    src     = inputs["data"]
    df_data = inputs["displacement_field"].data

    ux = np.real(df_data[0]).astype(np.float64)
    uy = np.real(df_data[1]).astype(np.float64)

    N  = src.data.shape[-1]
    x  = np.arange(N, dtype=np.float64)
    X, Y = np.meshgrid(x, x)
    X_df = (X - ux).astype(np.float64)
    Y_df = (Y - uy).astype(np.float64)

    out = np.zeros_like(src.data, dtype=np.float64)
    for i in range(src.data.shape[0]):
        px_itp = PixelInterpolation(
            src.data[i].astype(np.float64), X_df, Y_df,
            params["interpolate_method"],
            params["pad_method"],
        )
        out[i] = px_itp.dataMapping()

    return UdsDataStru(
        name         = src.name + "_lf",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
