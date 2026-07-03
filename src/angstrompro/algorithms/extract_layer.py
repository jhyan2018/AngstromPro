# -*- coding: utf-8 -*-
"""
Extract-layer process for AngstromPro.

Registered processes
--------------------
    spectral.extract_layer
        Extract a single layer from a 3-D stack as a new single-layer UDS.
        The layer axis value is preserved from the source.
        Name suffix: _l<index>
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
    name        = "spectral.extract_layer",
    label       = "Extract Layer",
    category    = "Spectral",
    schema      = ProcessSchema(
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack from which one layer will be extracted.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "layer_index",
                type        = int,
                default     = 0,
                label       = "Layer index",
                description = "Zero-based index of the layer to extract.",
                min         = 0,
            ),
        ],
    ),
    description = "Extract a single layer from a 3-D stack as a new single-layer UDS.",
)
def extract_layer(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]
    idx = params["layer_index"]

    n_layers = src.data.shape[0]
    if idx >= n_layers or idx < 0:
        raise ValueError(
            f"spectral.extract_layer: layer_index {idx} is out of range "
            f"for a stack with {n_layers} layers."
        )

    out = src.data[idx][np.newaxis].copy()

    ax0 = Axis(
        values = src.axes[0].values[idx : idx + 1].copy(),
        label  = src.axes[0].label,
        units  = src.axes[0].units,
    )

    return UdsDataStru(
        name         = src.name + f"_l{idx}",
        data         = out,
        axes         = [ax0,
                        copy.deepcopy(src.axes[1]),
                        copy.deepcopy(src.axes[2])],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
