# -*- coding: utf-8 -*-
"""
Extend-region process for AngstromPro.

Fills a full-FOV image by tiling a small ROI according to two lattice vectors.
For every pixel in the full image, it finds all lattice-equivalent points inside
the ROI (bilinear interpolation + average) and assigns that value.

The ROI is taken from the "interest_region" annotation (RegionData) on the item.

Registered processes
--------------------
    spatial.extend_region
        Extend the ROI of a 3-D stack over the full FOV using two lattice
        vectors (length + angle).  Name suffix: _ext.
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
# Core algorithm (ported from ScienceY/ImageProcess/ExtendSmallRegion.py)
# ---------------------------------------------------------------------------

def _interp2d_bilinear(img: np.ndarray, x: float, y: float) -> float:
    H, W = img.shape
    x = np.clip(x, 0, W - 1)
    y = np.clip(y, 0, H - 1)
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    x1, y1 = min(x0 + 1, W - 1), min(y0 + 1, H - 1)
    dx, dy = x - x0, y - y0
    return float(
        (1 - dx) * (1 - dy) * img[y0, x0] +
        dx       * (1 - dy) * img[y0, x1] +
        (1 - dx) * dy       * img[y1, x0] +
        dx       * dy       * img[y1, x1]
    )


def _interp2d_average(img: np.ndarray, coords: np.ndarray) -> float:
    if len(coords) == 0:
        raise ValueError("coords must contain at least one (x, y) pair")
    return float(np.mean([_interp2d_bilinear(img, x, y) for x, y in coords]))


def _vector_from_length_angle(length: float, degree: float) -> tuple[float, float]:
    theta = np.deg2rad(degree)
    return float(length * np.cos(theta)), float(length * np.sin(theta))


def _lattice_coefficients(a1, a2, P, roi_x0: int, roi_y0: int) -> tuple[float, float]:
    a1x, a1y = a1
    a2x, a2y = a2
    Px, Py   = P
    A = np.array([[a1x, a2x], [a1y, a2y]], dtype=np.float64)
    b = np.array([Px - roi_x0, Py - roi_y0], dtype=np.float64)
    if abs(np.linalg.det(A)) < 1e-12:
        raise ValueError("Lattice vectors a1 and a2 are linearly dependent.")
    m, n = np.linalg.solve(A, b)
    return float(m), float(n)


def _lattice_equiv_points_in_roi(a1, a2, m: float, n: float,
                                  roi_shape: tuple[int, int]) -> np.ndarray:
    H, W = map(int, roi_shape)
    a1x, a1y = a1
    a2x, a2y = a2
    A    = np.array([[a1x, a2x], [a1y, a2y]], dtype=np.float64)
    Ainv = np.linalg.inv(A)

    m_frac = float(m - np.floor(m))
    n_frac = float(n - np.floor(n))

    corners    = np.array([[0., 0.], [W-1., 0.], [0., H-1.], [W-1., H-1.]])
    corners_uv = (Ainv @ corners.T).T
    umin, vmin = corners_uv.min(axis=0)
    umax, vmax = corners_uv.max(axis=0)

    Mmin = int(np.floor(umin - m_frac)) - 1
    Mmax = int(np.ceil(umax  - m_frac)) + 1
    Nmin = int(np.floor(vmin - n_frac)) - 1
    Nmax = int(np.ceil(vmax  - n_frac)) + 1

    pts_list = []
    for M in range(Mmin, Mmax + 1):
        for N in range(Nmin, Nmax + 1):
            u, v = M + m_frac, N + n_frac
            x = u * a1x + v * a2x
            y = u * a1y + v * a2y
            if (0.0 <= x < W) and (0.0 <= y < H):
                pts_list.append([x, y])

    if not pts_list:
        return np.zeros((0, 2), dtype=np.float64)

    pts = np.array(pts_list, dtype=np.float64)
    _, idx = np.unique(np.round(pts, decimals=4), axis=0, return_index=True)
    return pts[np.sort(idx)]


def _extend_region_2d(img: np.ndarray, a1, a2, roi) -> np.ndarray:
    img = np.asarray(img)
    if img.ndim != 2:
        raise ValueError(f"img must be 2D, got shape {img.shape}")
    H, W = img.shape

    if len(roi) == 3:
        roi_x0, roi_y0, roi_size = roi
        roi_H = roi_W = int(roi_size)
    elif len(roi) == 4:
        roi_x0, roi_y0, roi_H, roi_W = roi
        roi_H, roi_W = int(roi_H), int(roi_W)
    else:
        raise ValueError("roi must be (x0, y0, size) or (x0, y0, H, W)")

    roi_x0, roi_y0 = int(roi_x0), int(roi_y0)
    y1, x1 = max(0, roi_y0), max(0, roi_x0)
    y2, x2 = min(H, roi_y0 + roi_H), min(W, roi_x0 + roi_W)
    if y2 <= y1 or x2 <= x1:
        raise ValueError("ROI is outside the image bounds or empty after clipping.")

    roi_img      = img[y1:y2, x1:x2]
    H_roi, W_roi = roi_img.shape
    a1_vec       = _vector_from_length_angle(float(a1[0]), float(a1[1]))
    a2_vec       = _vector_from_length_angle(float(a2[0]), float(a2[1]))

    out = np.empty((H, W), dtype=np.float64)
    for y_full in range(H):
        for x_full in range(W):
            m, n = _lattice_coefficients(a1_vec, a2_vec, (x_full, y_full), x1, y1)
            pts  = _lattice_equiv_points_in_roi(a1_vec, a2_vec, m, n, (H_roi, W_roi))
            out[y_full, x_full] = _interp2d_average(roi_img, pts)
    return out


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
            name        = "a1_length",
            type        = float,
            default     = 10.0,
            label       = "a1 length",
            description = "Length of lattice vector a1 (pixels).",
            min         = 0.1,
        ),
        ParameterSpec(
            name        = "a1_angle",
            type        = float,
            default     = 0.0,
            label       = "a1 angle (deg)",
            description = "Angle of lattice vector a1 in degrees (0 = rightward, clockwise).",
            min         = 0.0,
            max         = 360.0,
        ),
        ParameterSpec(
            name        = "a2_length",
            type        = float,
            default     = 10.0,
            label       = "a2 length",
            description = "Length of lattice vector a2 (pixels).",
            min         = 0.1,
        ),
        ParameterSpec(
            name        = "a2_angle",
            type        = float,
            default     = 90.0,
            label       = "a2 angle (deg)",
            description = "Angle of lattice vector a2 in degrees (0 = rightward, clockwise).",
            min         = 0.0,
            max         = 360.0,
        ),
    ],
    annotations=[
        AnnotationSpec(
            name     = "interest_region",
            role     = "interest_region",
            type_id  = "region",
            required = True,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Registered process
# ---------------------------------------------------------------------------

@register_process(
    name        = "spatial.extend_region_2d",
    label       = "Extend Region 2D",
    category    = "Spatial",
    schema      = _SCHEMA,
    description = "Tile the interest_region annotation over the full FOV "
                  "using two lattice vectors.",
)
def extend_region(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"spatial.extend_region_2d requires ndim=3; got shape {src.data.shape}.")

    if not annotations or "interest_region" not in annotations:
        raise ValueError(
            "spatial.extend_region_2d requires an 'interest_region' annotation. "
            "Use Points → 'Set Interest Region from Main' to define it first."
        )

    region = annotations["interest_region"]
    roi = (
        region.col_min,
        region.row_min,
        region.row_max - region.row_min,
        region.col_max - region.col_min,
    )
    a1 = (params["a1_length"], params["a1_angle"])
    a2 = (params["a2_length"], params["a2_angle"])

    out = np.empty_like(src.data, dtype=np.float64)
    for i in range(src.data.shape[0]):
        out[i] = _extend_region_2d(src.data[i], a1, a2, roi)

    return UdsDataStru(
        name         = src.name + "_ext",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
