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
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)


_OUT_GAP = [
    OutputSpec(type_id="uds", ndim=3, label="Gap Map", description="Gap energy map (1 × H × W)."),
    OutputSpec(
        type_id="uds",
        ndim=3,
        label="R² Fit Quality Map",
        description="Coefficient-of-determination map for the polynomial fit (1 × H × W).",
    ),
]


def _energy_value_range_to_indices(
    energies: np.ndarray,
    energy_min: float | None,
    energy_max: float | None,
) -> tuple[int, int]:
    """Map physical energy bounds to the nearest inclusive layer range."""
    if energies.size == 0:
        raise ValueError("Gap-map layer axis has no energy values.")
    if energy_min is None and energy_max is None:
        return 0, energies.size - 1

    lower = float(np.min(energies)) if energy_min is None else float(energy_min)
    upper = float(np.max(energies)) if energy_max is None else float(energy_max)
    if not np.isfinite(lower) or not np.isfinite(upper):
        raise ValueError("Gap-map energy bounds must be finite.")
    lower, upper = sorted((lower, upper))
    lower_index = int(np.argmin(np.abs(energies - lower)))
    upper_index = int(np.argmin(np.abs(energies - upper)))
    return min(lower_index, upper_index), max(lower_index, upper_index)


def _gap_map_core(data3d: np.ndarray, energies: np.ndarray,
                  order: int, energy_min: float | None,
                  energy_max: float | None):
    """Return (gapmap, R2map) as (1, H, W) float64 arrays."""
    energies = np.asarray(energies, dtype=np.float64)
    if energies.ndim != 1:
        raise ValueError("Gap-map energies must be a one-dimensional array.")
    if data3d.ndim != 3 or data3d.shape[0] != energies.size:
        raise ValueError(
            "Gap-map data must have shape (energy, height, width) matching "
            "the energy axis."
        )
    if not np.all(np.isfinite(energies)):
        raise ValueError("Gap-map energy values must all be finite.")

    energy_start, energy_end = _energy_value_range_to_indices(
        energies, energy_min, energy_max)
    e_slice = slice(energy_start, energy_end + 1)
    energy  = energies[e_slice]
    if energy.size < order + 1:
        raise ValueError(
            f"Polynomial order {order} requires at least {order + 1} "
            "energy points in the selected range."
        )
    if np.unique(energy).size < order + 1:
        raise ValueError(
            f"Polynomial order {order} requires at least {order + 1} "
            "distinct energy values."
        )

    H, W    = data3d.shape[-2], data3d.shape[-1]

    gapmap = np.zeros((H, W), dtype=np.float64)
    R2map  = np.zeros((H, W), dtype=np.float64)
    variance_tol = np.finfo(np.float64).eps * max(1, energy.size) * 16.0

    for X, Y in itertools.product(range(H), range(W)):
        dIdV = data3d[e_slice, X, Y].astype(np.float64)
        if not np.all(np.isfinite(dIdV)):
            continue

        # Scale the signal before fitting so R² and the constant-spectrum test
        # do not depend on whether the channel is stored in A, nA, or pA.
        signal_scale = np.max(np.abs(dIdV))
        if not np.isfinite(signal_scale) or signal_scale == 0.0:
            continue
        normalized = dIdV / signal_scale

        centered = normalized - normalized.mean()
        ss_tot = float(np.dot(centered, centered))
        if ss_tot <= variance_tol:
            # R² and a peak position are undefined for a constant spectrum.
            continue

        # Polynomial.fit maps the physical energy coordinate to a stable
        # internal interval, avoiding the ill-conditioned raw-energy
        # Vandermonde matrix used previously.
        fitted = np.polynomial.Polynomial.fit(energy, normalized, order)
        predicted = fitted(energy)
        residual = normalized - predicted
        ss_res = float(np.dot(residual, residual))
        R2map[X, Y] = 1.0 - ss_res / ss_tot

        # Find local maximum of fitted polynomial
        d1 = fitted.deriv(1)
        d2 = fitted.deriv(2)
        root_tol = np.finfo(np.float64).eps * 64.0
        real_roots = []
        for root in d1.roots():
            root = complex(root)
            if abs(root.imag) > root_tol * max(1.0, abs(root.real)):
                continue
            position = root.real
            if energy.min() <= position <= energy.max() and d2(position) < 0:
                real_roots.append(position)

        if real_roots:
            max_root = max(real_roots, key=lambda r: fitted(r))
        else:
            max_root = (energy.max() if fitted(energy.max()) >= fitted(energy.min())
                        else energy.min())

        gapmap[X, Y] = max_root

    return gapmap[np.newaxis], R2map[np.newaxis]


@register_process(
    name        = "spectral.gap_map_2d",
    label       = "Gap Map 2D",
    category    = "Spectroscopy & Profiles",
    schema      = ProcessSchema(
        outputs=_OUT_GAP,
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
                name        = "energy_min",
                type        = float,
                default     = None,
                label       = "Energy minimum",
                description = "Lower physical energy bound. The nearest recorded layer is used.",
                decimals    = 9,
                axis_input  = "data",
                axis_index  = 0,
                axis_default = "min",
            ),
            ParameterSpec(
                name        = "energy_max",
                type        = float,
                default     = None,
                label       = "Energy maximum",
                description = "Upper physical energy bound. The nearest recorded layer is used.",
                decimals    = 9,
                axis_input  = "data",
                axis_index  = 0,
                axis_default = "max",
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
        raise ValueError("spectral.gap_map_2d: layer axis has no energy values.")

    gm_data, r2_data = _gap_map_core(
        src.data, energies,
        params["order"],
        params.get("energy_min"),
        params.get("energy_max"),
    )

    gm = UdsDataStru(
        name         = src.name + "_gm",
        data         = gm_data,
        axes         = [Axis(values=np.array([0.0]), label="Gap",
                             units=src.axes[0].units),
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
