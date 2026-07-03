# -*- coding: utf-8 -*-
"""
Gap-map process for AngstromPro.

Registered processes
--------------------
    spectral.gap_map
        Fit a polynomial to dI/dV(E) at each pixel and extract the energy
        of the highest coherence peak (local maximum of the fit).
        Returns two workspace items: gap map (_gm) and R² map (_R2).
"""

from __future__ import annotations

import copy
import itertools

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)


def _gap_map_core(data3d: np.ndarray, energies: np.ndarray,
                  order: int, energy_start: int, energy_end: int):
    """Return (gapmap, R2map) as (1, H, W) float64 arrays."""
    if energy_end == -1:
        energy_end = len(energies) - 1

    e_slice = slice(energy_start, energy_end + 1)
    energy  = energies[e_slice]
    H, W    = data3d.shape[-2], data3d.shape[-1]

    # Build Vandermonde matrix once (energy_points × (order+1))
    A = np.column_stack([energy ** k for k in range(order + 1)])

    gapmap = np.zeros((H, W), dtype=np.float64)
    R2map  = np.zeros((H, W), dtype=np.float64)

    for X, Y in itertools.product(range(H), range(W)):
        dIdV = data3d[e_slice, X, Y].astype(np.float64)

        p, *_ = np.linalg.lstsq(A, dIdV, rcond=None)

        # R²
        dIdV_pred = A @ p
        ss_res = np.sum((dIdV - dIdV_pred) ** 2)
        ss_tot = np.sum((dIdV - dIdV.mean()) ** 2)
        R2map[X, Y] = (
            (1.0 - ss_res / ss_tot) if ss_tot >= 1e-15
            else (1.0 if ss_res < 1e-15 else 0.0)
        )

        # Find local maximum of fitted polynomial
        fitted     = np.poly1d(p[::-1])
        d1         = np.polyder(fitted, 1)
        d2         = np.polyder(fitted, 2)
        real_roots = [r.real for r in d1.r
                      if np.isreal(r)
                      and energy.min() <= r.real <= energy.max()
                      and d2(r.real) < 0]

        if real_roots:
            max_root = max(real_roots, key=lambda r: fitted(r))
        else:
            max_root = (energy.max() if fitted(energy.max()) >= fitted(energy.min())
                        else energy.min())

        gapmap[X, Y] = max_root

    return gapmap[np.newaxis], R2map[np.newaxis]


@register_process(
    name        = "spectral.gap_map",
    label       = "Gap Map",
    category    = "Spatial",
    schema      = ProcessSchema(
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "dI/dV 3D stack",
                description = "3-D dI/dV stack with energy as the layer axis.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "order",
                type        = int,
                default     = 2,
                label       = "Polynomial order",
                description = "Degree of the polynomial fitted to dI/dV(E) at each pixel. "
                              "2 = quadratic (fast); higher orders capture more complex peaks.",
                min         = 2,
                max         = 10,
            ),
            ParameterSpec(
                name        = "energy_start",
                type        = int,
                default     = 0,
                label       = "Energy start (layer index)",
                description = "First layer index included in the fit (0 = first layer).",
                min         = 0,
            ),
            ParameterSpec(
                name        = "energy_end",
                type        = int,
                default     = -1,
                label       = "Energy end (layer index)",
                description = "Last layer index included in the fit (-1 = last layer).",
                min         = -1,
            ),
        ],
    ),
    description = (
        "Fit a polynomial to dI/dV(E) at every pixel and extract the energy of "
        "the superconducting coherence peak (highest local maximum of the fit). "
        "Returns two items: gap map (_gm) and R² goodness-of-fit map (_R2)."
    ),
)
def gap_map(inputs: dict, params: dict, *, annotations=None) -> list:
    src      = inputs["data"]
    energies = src.axes[0].values.astype(np.float64)

    if len(energies) == 0:
        raise ValueError("spectral.gap_map: layer axis has no energy values.")

    gm_data, r2_data = _gap_map_core(
        src.data, energies,
        params["order"],
        params["energy_start"],
        params["energy_end"],
    )

    gm = UdsDataStru(
        name         = src.name + "_gm",
        data         = gm_data,
        axes         = [Axis(values=np.array([0.0]), label="Gap", units="V"),
                        copy.deepcopy(src.axes[1]),
                        copy.deepcopy(src.axes[2])],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
    r2 = UdsDataStru(
        name         = src.name + "_R2",
        data         = r2_data,
        axes         = [Axis(values=np.array([0.0]), label="R²", units=""),
                        copy.deepcopy(src.axes[1]),
                        copy.deepcopy(src.axes[2])],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
    return [gm, r2]
