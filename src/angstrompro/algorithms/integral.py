# -*- coding: utf-8 -*-
"""
Layer-integral process for AngstromPro.

Registered processes
--------------------
    spectral.integral
        Sum a contiguous range of layers along the layer axis, producing a
        single-layer UDS.  Physically equivalent to integrating dI/dV over
        a bias window.  Name suffix: _itg
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)


@register_process(
    name        = "spectral.integral",
    label       = "Layer Integral",
    category    = "Spectral",
    schema      = ProcessSchema(
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack to integrate along the layer axis.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "layer_start",
                type        = int,
                default     = 0,
                label       = "Layer start (index)",
                description = "First layer index included in the sum (0 = first layer).",
                min         = 0,
            ),
            ParameterSpec(
                name        = "layer_end",
                type        = int,
                default     = -1,
                label       = "Layer end (index)",
                description = "Last layer index included in the sum (-1 = last layer).",
                min         = -1,
            ),
        ],
    ),
    description = (
        "Sum layers layer_start to layer_end (inclusive) along the layer axis. "
        "Equivalent to integrating dI/dV over a bias window."
    ),
)
def integral(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src   = inputs["data"]
    start = params["layer_start"]
    end   = params["layer_end"]

    n_layers = src.data.shape[0]
    if end == -1:
        end = n_layers - 1

    if start < 0 or start >= n_layers:
        raise ValueError(
            f"spectral.integral: layer_start {start} out of range "
            f"for a stack with {n_layers} layers."
        )
    if end < start or end >= n_layers:
        raise ValueError(
            f"spectral.integral: layer_end {end} out of range or less than "
            f"layer_start {start} (stack has {n_layers} layers)."
        )

    out = src.data[start:end + 1].sum(axis=0)[np.newaxis]

    # Layer axis value: midpoint of the summed energy range
    mid_value = float(src.axes[0].values[start:end + 1].mean())
    ax0 = Axis(
        values = np.array([mid_value]),
        label  = src.axes[0].label,
        units  = src.axes[0].units,
    )

    return UdsDataStru(
        name         = src.name + "_itg",
        data         = out,
        axes         = [ax0,
                        copy.deepcopy(src.axes[1]),
                        copy.deepcopy(src.axes[2])],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
