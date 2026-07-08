# -*- coding: utf-8 -*-
"""
R-map process for AngstromPro.

Registered processes
--------------------
    spectral.r_map
        Compute the R-map: I(r, +E) / I(r, -E) for every matched ±E pair
        found in the energy axis.  Output layers correspond to positive
        energies only.  Name suffix: _rmp
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


def _find_pairs(energies: np.ndarray, tolerance: float) -> list[tuple[int, int, float]]:
    """Return (pos_idx, neg_idx, pos_energy) for every matched ±E pair.

    For each positive energy, the closest negative energy within `tolerance`
    is used as the counterpart.  Each layer is used at most once per side.
    """
    pos_indices = np.where(energies > 0)[0]
    neg_indices = np.where(energies < 0)[0]

    used_neg = set()
    pairs: list[tuple[int, int, float]] = []

    for pi in pos_indices:
        e = energies[pi]
        # distance between e and abs of each negative energy
        dists = np.abs(energies[neg_indices] + e)   # want energies[ni] ≈ -e
        best  = int(np.argmin(dists))
        if dists[best] <= tolerance:
            ni = neg_indices[best]
            if ni not in used_neg:
                used_neg.add(ni)
                pairs.append((int(pi), int(ni), float(e)))

    pairs.sort(key=lambda t: t[2])   # ascending positive energy
    return pairs


_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]


@register_process(
    name        = "spectral.r_map_2d",
    label       = "R-map 2D",
    category    = "Spatial",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "dI/dV 3D stack",
                description = "3-D dI/dV stack whose layer axis contains both "
                              "positive and negative bias values.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "tolerance",
                type        = float,
                default     = 1e-6,
                label       = "Energy tolerance",
                description = "Maximum allowed difference between +E and |−E| for a pair "
                              "to be considered matched (same units as the energy axis). "
                              "Increase if experimental bias steps are not exactly symmetric.",
                min         = 0.0,
            ),
        ],
    ),
    description = (
        "Compute R(r, E) = I(r, +E) / I(r, -E) for every matched ±E pair "
        "in the energy axis.  A tolerance parameter handles slight asymmetries "
        "in experimental bias values.  Output layers are indexed by positive energy."
    ),
)
def r_map(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src       = inputs["data"]
    energies  = src.axes[0].values.astype(np.float64)
    tolerance = params["tolerance"]

    pairs = _find_pairs(energies, tolerance)

    if not pairs:
        raise ValueError(
            "spectral.r_map_2d: no matching ±E pairs found within the given tolerance "
            f"({tolerance}). Try increasing the energy tolerance parameter."
        )

    H, W         = src.data.shape[-2], src.data.shape[-1]
    n            = len(pairs)
    out          = np.zeros((n, H, W), dtype=np.float64)
    out_energies = np.empty(n, dtype=np.float64)

    for i, (pi, ni, e) in enumerate(pairs):
        out[i]          = src.data[pi] / src.data[ni]
        out_energies[i] = e

    ax0 = Axis(
        values = out_energies,
        label  = src.axes[0].label,
        units  = src.axes[0].units,
    )
    return UdsDataStru(
        name         = src.name + "_rmp",
        data         = out,
        axes         = [ax0,
                        copy.deepcopy(src.axes[1]),
                        copy.deepcopy(src.axes[2])],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
