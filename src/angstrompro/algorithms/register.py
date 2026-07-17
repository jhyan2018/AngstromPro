# -*- coding: utf-8 -*-
"""
Image-registration process for AngstromPro.

Registered processes
--------------------
    spatial.register
        Fit an affine transform from three source→target point-pair
        correspondences and remap every layer of a 3-D stack back to the
        original spatial shape.  Name suffix: _rg

The two sets of three points are read from annotations on the primary item:
    register_points           — three points in the image to be aligned
                                (row, col in data pixel coordinates)
    register_reference_points — three corresponding target positions
                                (row, col in data pixel coordinates)
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
from .geometric_operation import AffineTransform


def _register(data3d: np.ndarray,
              src_pts: np.ndarray,
              tgt_pts: np.ndarray,
              ratio: float,
              interpolate_method: str,
              pad_method: str) -> np.ndarray:
    """Apply affine registration defined by three src→tgt point pairs.

    Parameters
    ----------
    src_pts, tgt_pts : ndarray (3, 2)
        Points in [row, col] order (data pixel coordinates).
    ratio : float
        Scale factor applied to tgt_pts before fitting: tgt_pts / ratio.
        Use ratio = ref_pixels / src_pixels when the reference points were
        picked from an image with a different pixel count than the source.
    """
    def _to_xy(pts):
        # convert [row, col] → (x=col, y=row) tuples expected by AffineTransform
        return [(float(pts[i, 1]), float(pts[i, 0])) for i in range(3)]

    tgt_pts_scaled = tgt_pts / ratio
    rPoints = _to_xy(src_pts) + _to_xy(tgt_pts_scaled)   # [src0,src1,src2, tgt0,tgt1,tgt2]

    affine = AffineTransform()
    affine.setAffineMatrixFrom3PairsRpoints(rPoints)
    affine.srcMappedPoints(data3d.shape[-2], data3d.shape[-1])

    out = np.zeros_like(data3d, dtype=np.float64)
    for i in range(data3d.shape[0]):
        out[i] = affine.affineMappingForRegister(
            data3d[i].astype(np.float64), interpolate_method, pad_method)
    return out


_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]


@register_process(
    name        = "spatial.register_2d",
    label       = "Register 2D",
    category    = "Spatial",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack to be registered. Must carry "
                              "'register_points' and 'register_reference_points' annotations.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "ratio",
                type        = float,
                default     = 1.0,
                label       = "Pixel ratio",
                description = "ref_pixels / src_pixels. Scales the reference points from "
                              "the reference image's pixel space into the source image's "
                              "pixel space before fitting the affine transform. "
                              "E.g. 4.0 if reference points were picked on a 1024×1024 "
                              "image but the source data is 256×256.",
                min         = 1e-6,
            ),
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
        annotations=[
            AnnotationSpec(
                name     = "register_points",
                role     = "register_points",
                type_id  = "point_set",
                required = True,
            ),
            AnnotationSpec(
                name     = "register_reference_points",
                role     = "register_reference_points",
                type_id  = "point_set",
                required = True,
            ),
        ],
    ),
    description = (
        "Fit an affine transform from three source→target point-pair correspondences "
        "and remap every layer back to the original spatial shape. "
        "Set 'register_points' (3 points on the image to align) and "
        "'register_reference_points' (3 corresponding target positions) as annotations first."
    ),
)
def register(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src      = inputs["data"]
    ann      = annotations or {}

    src_ann = ann.get("register_points")
    tgt_ann = ann.get("register_reference_points")

    if src_ann is None or not hasattr(src_ann, "coords"):
        raise ValueError(
            "spatial.register_2d: 'register_points' annotation is missing or invalid.")
    if tgt_ann is None or not hasattr(tgt_ann, "coords"):
        raise ValueError(
            "spatial.register_2d: 'register_reference_points' annotation is missing or invalid.")

    src_pts = src_ann.coords
    tgt_pts = tgt_ann.coords

    for name, pts in (("register_points", src_pts),
                      ("register_reference_points", tgt_pts)):
        if pts.shape[0] < 3:
            raise ValueError(
                f"spatial.register_2d: '{name}' requires exactly 3 points; "
                f"got {pts.shape[0]}."
            )

    out = _register(
        src.data,
        src_pts[:3],
        tgt_pts[:3],
        params["ratio"],
        params["interpolate_method"],
        params["pad_method"],
    )

    return UdsDataStru(
        name         = src.name + "_rg",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
