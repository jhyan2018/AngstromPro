# -*- coding: utf-8 -*-
"""
Normalisation process for AngstromPro.

Registered processes
--------------------
    spectral.normalize
        Divide each layer by its spatial pixel sum so every layer sums to 1.
        Preserves spatial distribution shape while removing layer-to-layer
        amplitude variation.  Name suffix: _nmz
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ProcessSchema,
    register_process,
)


_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]


@register_process(
    name        = "spectral.normalize_2d",
    label       = "Normalize 2D (per layer)",
    category    = "Spectral",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack to normalise. Each layer is divided by its "
                              "own spatial pixel sum independently.",
                ndim        = 3,
            ),
        ],
        params=[],
    ),
    description = (
        "L1-normalise each layer independently: output[i] = data[i] / sum(data[i]). "
        "Removes layer-to-layer amplitude variation; useful for comparing spatial "
        "patterns in dI/dV maps across bias voltages."
    ),
)
def normalize(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src  = inputs["data"]
    data = src.data.astype(np.float64)

    layer_sums = data.sum(axis=(1, 2), keepdims=True)  # (L, 1, 1)

    zero_mask = layer_sums == 0
    if zero_mask.any():
        raise ValueError(
            "spectral.normalize_2d: one or more layers have a zero pixel sum "
            "and cannot be normalised."
        )

    out = data / layer_sums

    return UdsDataStru(
        name         = src.name + "_nmz",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
