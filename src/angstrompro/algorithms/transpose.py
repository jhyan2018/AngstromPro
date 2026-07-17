# -*- coding: utf-8 -*-
"""
Created on Mon Jul  7 2026

@author: jiahaoYan

Axis transpose processes for AngstromPro.

Registered processes
--------------------
    common.transpose_1d
        Swap the two axes of a ndim=2 UDS (curve stack).
        Output shape: (n_pts, n_curves) if input is (n_curves, n_pts).

    common.transpose_2d
        Reorder the three axes of a ndim=3 UDS (image stack).
        User specifies new axis order as a comma-separated string, e.g. "2,0,1".
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


_OUT_2D = [OutputSpec(type_id="uds", ndim=2, label="Curve Stack", description="ndim=2 UDS (curves × points).")]
_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]


@register_process(
    name        = "common.transpose_1d",
    label       = "Transpose 1D (swap axes)",
    category    = "Common",
    schema      = ProcessSchema(
        outputs=_OUT_2D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "Curve Stack",
                description = "ndim=2 UDS whose two axes will be swapped.",
                ndim        = 2,
            ),
        ],
    ),
    description = (
        "Swap the two axes of a ndim=2 (curve stack) UDS. "
        "axis[0] ↔ axis[1]. Use to change which axis is treated as the "
        "processing axis (axis[-1]) before running a 1D process."
    ),
)
def transpose_1d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src  = inputs["data"]
    data = np.transpose(src.data)          # (n, m) → (m, n)
    axes = [copy.deepcopy(src.axes[1]),
            copy.deepcopy(src.axes[0])]
    return UdsDataStru(
        name         = src.name + "_T",
        data         = data.copy(),
        axes         = axes,
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )


@register_process(
    name        = "common.transpose_2d",
    label       = "Transpose 2D (reorder axes)",
    category    = "Common",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "Image Stack",
                description = "ndim=3 UDS whose axes will be reordered.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "axis_order",
                type        = str,
                default     = "0,1,2",
                label       = "New axis order",
                description = (
                    "Comma-separated permutation of axis indices. "
                    "e.g. '2,0,1' moves axis[2] to position 0. "
                    "Check inspector for current axis[0], axis[1], axis[2] types."
                ),
            ),
        ],
    ),
    description = (
        "Reorder the three axes of a ndim=3 (image stack) UDS. "
        "Specify new axis order as e.g. '2,0,1'. "
        "axis types and labels travel with their axes. "
        "Use to move the processing axis to axis[-1] before running a 2D process."
    ),
)
def transpose_2d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]

    try:
        order = [int(x.strip()) for x in params["axis_order"].split(",")]
    except ValueError:
        raise ValueError(
            f"common.transpose_2d: 'axis_order' must be three comma-separated "
            f"integers, e.g. '2,0,1'. Got: {params['axis_order']!r}"
        )

    ndim = src.data.ndim
    if len(order) != ndim or sorted(order) != list(range(ndim)):
        raise ValueError(
            f"common.transpose_2d: axis_order {order} is not a valid "
            f"permutation of [0, 1, 2] for ndim={ndim}."
        )

    data = np.transpose(src.data, order)
    axes = [copy.deepcopy(src.axes[i]) for i in order]

    suffix = "_T" + "".join(str(i) for i in order)
    return UdsDataStru(
        name         = src.name + suffix,
        data         = data.copy(),
        axes         = axes,
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
