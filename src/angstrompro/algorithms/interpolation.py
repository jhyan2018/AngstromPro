# -*- coding: utf-8 -*-
"""
Structured 2x spatial interpolation process for AngstromPro.

Registered processes
--------------------
    spatial.interpolate
        Upsample each layer by 2x using structured (bilinear) interpolation:
        midpoints are inserted between every pair of adjacent pixels in both
        spatial dimensions.  Output shape: (L, 2N-1, 2M-1).
        Spatial axis values are interleaved to match the new pixel grid.
        Name suffix: _ip
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ProcessSchema,
    register_process,
)


def _interleave_axis(values: np.ndarray) -> np.ndarray:
    """Insert midpoints between every pair of adjacent values: length N → 2N-1."""
    out = np.empty(2 * len(values) - 1, dtype=np.float64)
    out[::2]  = values
    out[1::2] = (values[:-1] + values[1:]) / 2
    return out


def _interpolate_2x(data3d: np.ndarray) -> np.ndarray:
    """2x structured upsampling for each layer independently."""
    L, N, M = data3d.shape
    out = np.zeros((L, 2 * N - 1, 2 * M - 1), dtype=np.float64)
    for i in range(L):
        layer       = data3d[i].astype(np.float64)
        out[i, ::2,  ::2]  = layer
        out[i, ::2,  1::2] = (layer[:, :-1] + layer[:, 1:]) / 2
        out[i, 1::2, ::2]  = (layer[:-1, :] + layer[1:, :]) / 2
        out[i, 1::2, 1::2] = (layer[:-1, :-1] + layer[1:, :-1] +
                               layer[:-1, 1:]  + layer[1:, 1:])  / 4
    return out


_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]


@register_process(
    name        = "spatial.interpolate_2d",
    label       = "Interpolate 2D (2x)",
    category    = "Spatial",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack to upsample. Output spatial dims become (2N-1, 2M-1).",
                ndim        = 3,
            ),
        ],
        params=[],
    ),
    description = (
        "Structured 2x spatial upsampling: inserts bilinearly interpolated midpoints "
        "between every pair of adjacent pixels in both spatial dimensions. "
        "Output shape: (L, 2N-1, 2M-1). Spatial axis values are interleaved to match."
    ),
)
def interpolate(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src  = inputs["data"]
    out  = _interpolate_2x(src.data)

    ax1 = Axis(
        values = _interleave_axis(src.axes[1].values),
        label  = src.axes[1].label,
        units  = src.axes[1].units,
    )
    ax2 = Axis(
        values = _interleave_axis(src.axes[2].values),
        label  = src.axes[2].label,
        units  = src.axes[2].units,
    )

    return UdsDataStru(
        name         = src.name + "_ip",
        data         = out,
        axes         = [copy.deepcopy(src.axes[0]), ax1, ax2],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
