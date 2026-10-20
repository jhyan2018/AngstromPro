# -*- coding: utf-8 -*-
"""Internal affine lattice corrections; no process registrations.

Peak coordinates are columns/rows in the shifted FFT of the real-space input.
The original square and hexagonal calculations are kept unchanged here.
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from ..geometric_operation import AffineTransform


def _rebuild_axes(src: UdsDataStru, new_h: int, new_w: int) -> list:
    """Rebuild spatial axes for the affine-corrected output using the original pixel spacing."""
    ax0 = copy.deepcopy(src.axes[0])

    d_row = (
        float(src.axes[1].values[1] - src.axes[1].values[0])
        if len(src.axes[1].values) > 1
        else 1.0
    )
    d_col = (
        float(src.axes[2].values[1] - src.axes[2].values[0])
        if len(src.axes[2].values) > 1
        else 1.0
    )

    ax1 = Axis(
        values=d_row * np.arange(new_h),
        label=src.axes[1].label,
        units=src.axes[1].units,
        ticks={},
    )
    ax2 = Axis(
        values=d_col * np.arange(new_w),
        label=src.axes[2].label,
        units=src.axes[2].units,
        ticks={},
    )
    return [ax0, ax1, ax2]


def _apply_affine(
    src: UdsDataStru,
    affine: AffineTransform,
    interpolate_method: str = "bilinear",
    pad_method: str = "constant",
) -> UdsDataStru:
    n_layers = src.data.shape[0]
    out_h = affine.src_X_float.shape[-2]
    out_w = affine.src_X_float.shape[-1]
    out = np.zeros((n_layers, out_h, out_w), dtype=np.float64)
    for i in range(n_layers):
        out[i] = affine.affineMapping(src.data[i], interpolate_method, pad_method)
    return UdsDataStru(
        name=src.name + "_pl",
        data=out,
        axes=_rebuild_axes(src, out_h, out_w),
        info=dict(src.info),
        proc_history=[copy.deepcopy(r) for r in src.proc_history],
    )


# ---------------------------------------------------------------------------
# Core algorithms (ported from ScienceY/ImageProcess/PerfectLattice.py)
# ---------------------------------------------------------------------------


def perfect_lattice_square(
    src: UdsDataStru,
    bPx1,
    bPy1,
    bPx2,
    bPy2,
    interpolate_method: str = "bilinear",
    pad_method: str = "constant",
) -> UdsDataStru:
    affine = AffineTransform()

    Ox = (src.data.shape[-1] - src.data.shape[-1] % 2) / 2
    Oy = (src.data.shape[-2] - src.data.shape[-2] % 2) / 2

    Q1 = np.array([bPx1 - Ox, bPy1 - Oy])
    Q2 = np.array([bPx2 - Ox, bPy2 - Oy])
    Q_ref = np.array([-Ox, 0.0])

    Q1_mag = np.linalg.norm(Q1)
    Q2_mag = np.linalg.norm(Q2)
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


def perfect_lattice_hexagonal(
    src: UdsDataStru,
    bPx1,
    bPy1,
    bPx2,
    bPy2,
    interpolate_method: str = "bilinear",
    pad_method: str = "constant",
) -> UdsDataStru:
    affine = AffineTransform()

    Ox = (src.data.shape[-1] - src.data.shape[-1] % 2) / 2
    Oy = (src.data.shape[-2] - src.data.shape[-2] % 2) / 2

    Q1 = np.array([bPx1 - Ox, bPy1 - Oy])
    Q2 = np.array([bPx2 - Ox, bPy2 - Oy])
    Q_ref = np.array([-Ox, 0.0])

    Q1_mag = np.linalg.norm(Q1)
    Q2_mag = np.linalg.norm(Q2)
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
        by = 1.0 / np.tan(theta2) - Q1_mag * np.cos(np.pi / 3) / (
            Q2_mag * np.sin(theta2)
        )

    sy = Q2_mag * np.sin(theta2) / (Q1_mag * np.sin(np.pi / 3))

    affine.setRotateOfAffineMatrix(-theta1)
    affine.setShearOfAffineMatrix(0.0, by)
    affine.setScaleOfAffineMatrix(1.0, sy)
    affine.setRotateOfAffineMatrix(theta1)
    affine.srcMappedPoints(src.data.shape[-2], src.data.shape[-1])

    return _apply_affine(src, affine, interpolate_method, pad_method)
