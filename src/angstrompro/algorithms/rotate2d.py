# -*- coding: utf-8 -*-
"""
2-D rotation process for AngstromPro.

Registered processes
--------------------
    spatial.rotate2d
        Rotate every layer of a 3-D stack by a given angle (degrees).
        Name suffix: _rot.
"""

from __future__ import annotations

import copy

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)
from .geometric_operation import rotate2d

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
            name        = "theta",
            type        = float,
            default     = 0.0,
            label       = "Angle (deg)",
            description = "Counter-clockwise rotation angle in degrees.",
            min         = -360.0,
            max         =  360.0,
        ),
        ParameterSpec(
            name        = "interpolate_method",
            type        = str,
            default     = "bilinear",
            label       = "Interpolation",
            description = "Pixel interpolation method used during rotation.",
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
)


@register_process(
    name        = "spatial.rotate2d",
    label       = "Rotate 2D",
    category    = "Spatial",
    schema      = _SCHEMA,
    description = "Rotate every layer of a 3-D stack counter-clockwise by a given angle.",
)
def rotate2d_process(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(f"spatial.rotate2d requires ndim=3; got shape {src.data.shape}.")

    out = rotate2d(src.data, params["theta"],
                   params["interpolate_method"], params["pad_method"])

    return UdsDataStru(
        name         = src.name + "_rot",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
