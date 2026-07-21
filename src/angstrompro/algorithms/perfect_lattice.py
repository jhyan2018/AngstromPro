# -*- coding: utf-8 -*-
"""
Perfect-lattice correction processes for AngstromPro.

Uses an affine transform derived from two Bragg peaks to correct lattice
distortions (shear, unequal scaling) in real-space STM images.

The two Bragg peaks are read from the "bragg_peaks" annotation
(PointSetData, [row, col] coords) stored on the FFT/k-space item.
The first two points are used as Q1 and Q2.

Registered processes
--------------------
    spatial.perfect_lattice_square
        Correct a square lattice: forces Q1 ⊥ Q2 and |Q1| = |Q2|.
        Name suffix: _pl.

    spatial.perfect_lattice_hexagonal
        Correct a hexagonal lattice: forces Q1 and Q2 to 60° with
        equal magnitude.  Q2 must be clockwise from Q1.
        Name suffix: _pl.
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)
from angstrompro.core.processes.param_schema import AnnotationSpec
from .geometric_operation import AffineTransform

# ---------------------------------------------------------------------------
# Shared schema
# ---------------------------------------------------------------------------

_ANNOTATION = AnnotationSpec(
    name     = "bragg_peaks",
    role     = "bragg_peaks",
    type_id  = "point_set",
    required = True,
)

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

_SCHEMA = ProcessSchema(
    outputs=_OUT_3D,
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "3D Stack",
            description = "UdsDataStru with ndim=3 (layers × rows × cols). "
                          "Typically the FFT/k-space item whose bragg_peaks annotation "
                          "holds the two Q-vectors to use for correction.",
            ndim        = 3,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "interpolate_method",
            type        = str,
            default     = "bilinear",
            label       = "Interpolation",
            description = "Pixel interpolation method used during the affine remap.",
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
    annotations=[_ANNOTATION],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_bragg_peaks(annotations: dict | None):
    if not annotations or "bragg_peaks" not in annotations:
        raise ValueError(
            "perfect_lattice requires a 'bragg_peaks' annotation with at least 2 points. "
            "Use Points → 'Set Bragg Peaks from Aux' to define them first."
        )
    coords = annotations["bragg_peaks"].coords   # (N, 2) [row, col]
    if coords.shape[0] < 2:
        raise ValueError(
            f"perfect_lattice requires at least 2 Bragg peaks; got {coords.shape[0]}."
        )
    # Return as (col, row) = (x, y) to match the old convention
    bPx1, bPy1 = float(coords[0, 1]), float(coords[0, 0])
    bPx2, bPy2 = float(coords[1, 1]), float(coords[1, 0])
    return bPx1, bPy1, bPx2, bPy2


def _rebuild_axes(src: UdsDataStru, new_h: int, new_w: int) -> list:
    """Rebuild spatial axes for the affine-corrected output using the original pixel spacing."""
    ax0 = copy.deepcopy(src.axes[0])

    d_row = float(src.axes[1].values[1] - src.axes[1].values[0]) if len(src.axes[1].values) > 1 else 1.0
    d_col = float(src.axes[2].values[1] - src.axes[2].values[0]) if len(src.axes[2].values) > 1 else 1.0

    ax1 = Axis(
        values = d_row * np.arange(new_h),
        label  = src.axes[1].label,
        units  = src.axes[1].units,
        ticks  = {},
    )
    ax2 = Axis(
        values = d_col * np.arange(new_w),
        label  = src.axes[2].label,
        units  = src.axes[2].units,
        ticks  = {},
    )
    return [ax0, ax1, ax2]


def _apply_affine(src: UdsDataStru, affine: AffineTransform,
                  interpolate_method: str = 'bilinear',
                  pad_method: str = 'constant') -> UdsDataStru:
    n_layers = src.data.shape[0]
    out_h    = affine.src_X_float.shape[-2]
    out_w    = affine.src_X_float.shape[-1]
    out      = np.zeros((n_layers, out_h, out_w), dtype=np.float64)
    for i in range(n_layers):
        out[i] = affine.affineMapping(src.data[i], interpolate_method, pad_method)
    return UdsDataStru(
        name         = src.name + "_pl",
        data         = out,
        axes         = _rebuild_axes(src, out_h, out_w),
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )

# ---------------------------------------------------------------------------
# Core algorithms (ported from ScienceY/ImageProcess/PerfectLattice.py)
# ---------------------------------------------------------------------------

def _perfect_lattice_square(src: UdsDataStru, bPx1, bPy1, bPx2, bPy2,
                            interpolate_method: str = 'bilinear',
                            pad_method: str = 'constant') -> UdsDataStru:
    affine = AffineTransform()

    Ox = (src.data.shape[-1] - src.data.shape[-1] % 2) / 2
    Oy = (src.data.shape[-2] - src.data.shape[-2] % 2) / 2

    Q1 = np.array([bPx1 - Ox, bPy1 - Oy])
    Q2 = np.array([bPx2 - Ox, bPy2 - Oy])
    Q_ref = np.array([-Ox, 0.0])

    Q1_mag   = np.linalg.norm(Q1)
    Q2_mag   = np.linalg.norm(Q2)
    Q_ref_mag = np.linalg.norm(Q_ref)

    theta1 = np.arccos(np.dot(Q1, Q_ref) / (Q1_mag * Q_ref_mag))
    theta2 = np.arccos(np.clip(np.dot(Q1, Q2) / (Q1_mag * Q2_mag), -1.0, 1.0))

    by = 0.0 if theta2 == np.pi / 2 else 1.0 / np.tan(theta2)
    sy = Q2_mag * np.sin(theta2) / Q1_mag

    affine.setRotateOfAffineMatrix(-theta1)
    affine.setShearOfAffineMatrix(0.0, by)
    affine.setScaleOfAffineMatrix(1.0, sy)
    affine.setRotateOfAffineMatrix(theta1)
    affine.srcMappedPoints(src.data.shape[-2], src.data.shape[-1])

    return _apply_affine(src, affine, interpolate_method, pad_method)


def _perfect_lattice_hexagonal(src: UdsDataStru, bPx1, bPy1, bPx2, bPy2,
                               interpolate_method: str = 'bilinear',
                               pad_method: str = 'constant') -> UdsDataStru:
    affine = AffineTransform()

    Ox = (src.data.shape[-1] - src.data.shape[-1] % 2) / 2
    Oy = (src.data.shape[-2] - src.data.shape[-2] % 2) / 2

    Q1 = np.array([bPx1 - Ox, bPy1 - Oy])
    Q2 = np.array([bPx2 - Ox, bPy2 - Oy])
    Q_ref = np.array([-Ox, 0.0])

    Q1_mag   = np.linalg.norm(Q1)
    Q2_mag   = np.linalg.norm(Q2)
    Q_ref_mag = np.linalg.norm(Q_ref)

    theta1 = np.arccos(np.dot(Q1, Q_ref) / (Q1_mag * Q_ref_mag))
    if Q1[1] > 0:
        theta1 = -theta1
    elif Q1[1] == 0:
        theta1 = 0.0

    theta2 = np.arccos(np.clip(np.dot(Q1, Q2) / (Q1_mag * Q2_mag), -1.0, 1.0))

    if theta2 == np.pi / 3:
        by = 0.0
    else:
        by = 1.0 / np.tan(theta2) - Q1_mag * np.cos(np.pi / 3) / (Q2_mag * np.sin(theta2))

    sy = Q2_mag * np.sin(theta2) / (Q1_mag * np.sin(np.pi / 3))

    affine.setRotateOfAffineMatrix(-theta1)
    affine.setShearOfAffineMatrix(0.0, by)
    affine.setScaleOfAffineMatrix(1.0, sy)
    affine.setRotateOfAffineMatrix(theta1)
    affine.srcMappedPoints(src.data.shape[-2], src.data.shape[-1])

    return _apply_affine(src, affine, interpolate_method, pad_method)

# ---------------------------------------------------------------------------
# Registered processes
# ---------------------------------------------------------------------------

@register_process(
    name        = "spatial.perfect_lattice_square_2d",
    label       = "Perfect Lattice Square 2D",
    category    = "Lattice & Registration",
    schema      = _SCHEMA,
    description = "Correct a square-lattice distortion using two Bragg peaks from the "
                  "bragg_peaks annotation.",
)
def perfect_lattice_square(inputs: dict, params: dict,
                            *, annotations: dict | None = None) -> UdsDataStru:
    src = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"spatial.perfect_lattice_square_2d requires ndim=3; got {src.data.shape}.")
    bPx1, bPy1, bPx2, bPy2 = _read_bragg_peaks(annotations)
    return _perfect_lattice_square(src, bPx1, bPy1, bPx2, bPy2,
                                   params["interpolate_method"], params["pad_method"])


@register_process(
    name        = "spatial.perfect_lattice_hexagonal_2d",
    label       = "Perfect Lattice Hexagonal 2D",
    category    = "Lattice & Registration",
    schema      = _SCHEMA,
    description = "Correct a hexagonal-lattice distortion using two Bragg peaks from the "
                  "bragg_peaks annotation. Q2 must be clockwise from Q1 at ~60°.",
)
def perfect_lattice_hexagonal(inputs: dict, params: dict,
                               *, annotations: dict | None = None) -> UdsDataStru:
    src = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"spatial.perfect_lattice_hexagonal_2d requires ndim=3; got {src.data.shape}.")
    bPx1, bPy1, bPx2, bPy2 = _read_bragg_peaks(annotations)
    return _perfect_lattice_hexagonal(src, bPx1, bPy1, bPx2, bPy2,
                                      params["interpolate_method"], params["pad_method"])
