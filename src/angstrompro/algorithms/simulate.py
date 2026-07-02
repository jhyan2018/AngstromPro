# -*- coding: utf-8 -*-
"""
Image-simulation processes for AngstromPro.

All algorithms are self-contained (no ScienceY imports).

Registered processes
--------------------
    simulate.heaviside2d
        Step-edge (Heaviside) image: ones on one side, zeros on the other.

    simulate.circle2d
        Filled-circle image (binary mask).

    simulate.gaussian2d
        Single 2-D Gaussian peak.

    simulate.sinusoidal2d
        Sum of up to 3 sinusoidal waves (superposition of plane waves).

    simulate.perfect_lattice2d
        Gaussian-atom lattice with arbitrary lattice vectors and optional
        sub-lattice phase modulation.

    simulate.lattice2d_line_domain_wall
        Same as perfect_lattice2d but with a line domain wall (half-unit-cell
        shift along x past the image midpoint).

    simulate.lattice2d_periodic_distortion
        Same as perfect_lattice2d but with a periodic distortion field
        (charge-density-wave-like displacement).
"""

from __future__ import annotations

import numpy as np

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

# ─── helpers ─────────────────────────────────────────────────────────────────

def _pixel_axes(n_layers: int, n_rows: int, n_cols: int) -> list:
    return [
        Axis(values=np.arange(n_layers, dtype=np.float64), label="Layer",  units=""),
        Axis(values=np.arange(n_rows,   dtype=np.float64), label="Row",    units="px"),
        Axis(values=np.arange(n_cols,   dtype=np.float64), label="Column", units="px"),
    ]


def _wrap(data2d: np.ndarray, name: str) -> UdsDataStru:
    """Wrap a 2-D array as a single-layer UdsDataStru."""
    d = data2d[np.newaxis, :, :]
    return UdsDataStru(
        name=name, data=d,
        axes=_pixel_axes(1, data2d.shape[0], data2d.shape[1]),
        info={"LayerValue": "0"},
        proc_history=[],
    )


# ─── curve primitives (inlined from GenerateCurve2D) ─────────────────────────

def _sinusoidal2d(size: int, qx: float, qy: float, phase: float,
                  amplitude: float = 1.0) -> np.ndarray:
    """cos(2π(qx·X + qy·Y)/size − phase)."""
    x = np.arange(size)
    X, Y = np.meshgrid(x, x)
    return amplitude * np.cos(2 * np.pi * (qx / size) * X
                              + 2 * np.pi * (qy / size) * Y
                              - phase)


def _gaussian2d(size: int, sigma: float,
                center_x: float = 0.0, center_y: float = 0.0) -> np.ndarray:
    """2-D Gaussian; center_x/y are offsets from image centre (pixels)."""
    x = np.arange(size)
    X, Y = np.meshgrid(x, x)
    cx = (size - size % 2) / 2 + center_x
    cy = (size - size % 2) / 2 + center_y
    return np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * sigma ** 2))


def _circle2d(size: int, radius: float,
              center_x: float = 0.0, center_y: float = 0.0) -> np.ndarray:
    """Binary filled circle; center_x/y are offsets from image centre (pixels)."""
    x = np.arange(size)
    X, Y = np.meshgrid(x, x)
    cx = (size - size % 2) / 2 + center_x
    cy = (size - size % 2) / 2 + center_y
    return (np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) < radius).astype(np.float64)


# ─── lattice generator (inlined from GenerateLattice2D) ──────────────────────

class _GenerateLattice2D:
    """Builds a 2-D Gaussian-atom lattice on a mesh of m×n unit cells."""

    def __init__(self, m: int, n: int,
                 a1x: float, a1y: float,
                 a2x: float, a2y: float,
                 Ox: float = 0.0, Oy: float = 0.0):
        M, N = np.meshgrid(np.arange(m), np.arange(n))
        self.latticeSitesX = M * a1x + N * a2x + Ox
        self.latticeSitesY = M * a1y + N * a2y + Oy
        self.a1 = np.sqrt(a1x ** 2 + a1y ** 2)
        self.a2 = np.sqrt(a2x ** 2 + a2y ** 2)
        self.M, self.N = M, N
        self.a1x, self.a1y = a1x, a1y
        self.a2x, self.a2y = a2x, a2y
        self._dispX = np.zeros_like(self.latticeSitesX)
        self._dispY = np.zeros_like(self.latticeSitesY)

    def set_displacement_line_domain_wall(self, shift_distance: float):
        n_cols = self._dispX.shape[-1]
        mask = np.arange(n_cols) > n_cols / 2   # right half
        self._dispX[:, mask] = shift_distance * min(self.a1, self.a2)
        self.latticeSitesX += self._dispX
        self.latticeSitesY += self._dispY

    def set_displacement_periodic(self,
                                  d1x: float, d1y: float,
                                  d2x: float, d2y: float,
                                  dp_a1: float = 0.1, dp_a2: float = 0.1,
                                  dphi1: float = 0.0, dphi2: float = 0.0):
        if d1x != 0:
            self._dispX += (dp_a1 * self.a1) * np.cos(
                2 * np.pi * self.M * (self.a1x / d1x) + dphi1)
        if d2x != 0:
            self._dispX += (dp_a2 * self.a2) * np.cos(
                2 * np.pi * self.N * (self.a2x / d2x) + dphi2)
        if d1y != 0:
            self._dispY += (dp_a1 * self.a1) * np.cos(
                2 * np.pi * self.M * (self.a1y / d1y) + dphi1)
        if d2y != 0:
            self._dispY += (dp_a2 * self.a2) * np.cos(
                2 * np.pi * self.N * (self.a2y / d2y) + dphi2)
        self.latticeSitesX += self._dispX
        self.latticeSitesY += self._dispY

    def generate(self, atom_size: float | None = None,
                 p1: float = 1.0, p2: float = 1.0) -> np.ndarray:
        if atom_size is None:
            atom_size = min(self.a1, self.a2) / 2
        sigma = 0.2 * atom_size

        x_range = int(np.ceil(self.latticeSitesX.max() - self.latticeSitesX.min()))
        y_range = int(np.ceil(self.latticeSitesY.max() - self.latticeSitesY.min()))
        size    = max(x_range, y_range)
        cx      = (size - size % 2) / 2
        cy      = (size - size % 2) / 2

        out = np.zeros((size, size))
        for col in range(self.latticeSitesX.shape[-1]):
            for row in range(self.latticeSitesX.shape[-2]):
                phase = 2 * np.pi * (col / p1 + row / p2)
                dx = self.latticeSitesX[row, col] - cx
                dy = self.latticeSitesY[row, col] - cy
                out += np.cos(phase) * _gaussian2d(size, sigma, dx, dy)
        return out


# ─── schemas ─────────────────────────────────────────────────────────────────

_SIZE_PARAM = ParameterSpec(
    name="size", type=int, default=256, label="Size (px)",
    description="Image width = height in pixels.", min=16, max=4096,
)

_LATTICE_PARAMS = [
    ParameterSpec(name="m",   type=int,   default=10,  label="m cells",
                  description="Number of unit cells along a1.", min=1, max=500),
    ParameterSpec(name="n",   type=int,   default=10,  label="n cells",
                  description="Number of unit cells along a2.", min=1, max=500),
    ParameterSpec(name="a1x", type=float, default=20.0, label="a1x (px)",
                  description="x-component of lattice vector a1 (pixels)."),
    ParameterSpec(name="a1y", type=float, default=0.0,  label="a1y (px)",
                  description="y-component of lattice vector a1 (pixels)."),
    ParameterSpec(name="a2x", type=float, default=0.0,  label="a2x (px)",
                  description="x-component of lattice vector a2 (pixels)."),
    ParameterSpec(name="a2y", type=float, default=20.0, label="a2y (px)",
                  description="y-component of lattice vector a2 (pixels)."),
    ParameterSpec(name="atom_size", type=float, default=0.0, label="Atom size (px)",
                  description="Gaussian atom radius in pixels. 0 = auto (half lattice spacing)."),
    ParameterSpec(name="Ox",  type=float, default=0.0, label="Origin x (px)",
                  description="x offset of the lattice origin (pixels)."),
    ParameterSpec(name="Oy",  type=float, default=0.0, label="Origin y (px)",
                  description="y offset of the lattice origin (pixels)."),
]

# ─── simulate.heaviside2d ────────────────────────────────────────────────────

@register_process(
    name="simulate.heaviside2d",
    label="Heaviside Step Edge 2D",
    category="Simulate",
    schema=ProcessSchema(
        inputs=[],
        params=[
            _SIZE_PARAM,
            ParameterSpec(name="edge_x", type=int, default=0, label="Edge X (px)",
                          description="Column index of the step edge. Negative = right half is zero."),
            ParameterSpec(name="edge_y", type=int, default=0, label="Edge Y (px)",
                          description="Row index of the step edge. Negative = lower half is zero."),
        ],
    ),
    description="Generate a step-edge (Heaviside) image: 1 on one side, 0 on the other.",
)
def heaviside2d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    size   = params["size"]
    edge_x = params["edge_x"]
    edge_y = params["edge_y"]

    data = np.ones((size, size), dtype=np.float64)
    if edge_x >= 0:
        lx, rx = 0, abs(edge_x)
    else:
        lx, rx = abs(edge_x), size
    if edge_y >= 0:
        ly, ry = 0, abs(edge_y)
    else:
        ly, ry = abs(edge_y), size
    data[ly:ry, lx:rx] = 0.0

    return _wrap(data, "sim_heaviside2d")


# ─── simulate.circle2d ───────────────────────────────────────────────────────

@register_process(
    name="simulate.circle2d",
    label="Circle 2D",
    category="Simulate",
    schema=ProcessSchema(
        inputs=[],
        params=[
            _SIZE_PARAM,
            ParameterSpec(name="radius",   type=float, default=50.0, label="Radius (px)",
                          description="Circle radius in pixels.", min=0.5),
            ParameterSpec(name="center_x", type=float, default=0.0,  label="Centre x offset (px)",
                          description="Horizontal offset from image centre (pixels)."),
            ParameterSpec(name="center_y", type=float, default=0.0,  label="Centre y offset (px)",
                          description="Vertical offset from image centre (pixels)."),
        ],
    ),
    description="Generate a binary filled-circle image.",
)
def circle2d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    data = _circle2d(params["size"], params["radius"],
                     params["center_x"], params["center_y"])
    return _wrap(data, "sim_circle2d")


# ─── simulate.gaussian2d ─────────────────────────────────────────────────────

@register_process(
    name="simulate.gaussian2d",
    label="Gaussian Peak 2D",
    category="Simulate",
    schema=ProcessSchema(
        inputs=[],
        params=[
            _SIZE_PARAM,
            ParameterSpec(name="sigma",    type=float, default=20.0, label="Sigma (px)",
                          description="Gaussian standard deviation in pixels.", min=0.1),
            ParameterSpec(name="center_x", type=float, default=0.0,  label="Centre x offset (px)",
                          description="Horizontal offset from image centre (pixels)."),
            ParameterSpec(name="center_y", type=float, default=0.0,  label="Centre y offset (px)",
                          description="Vertical offset from image centre (pixels)."),
        ],
    ),
    description="Generate a single 2-D Gaussian peak.",
)
def gaussian2d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    data = _gaussian2d(params["size"], params["sigma"],
                       params["center_x"], params["center_y"])
    return _wrap(data, "sim_gaussian2d")


# ─── simulate.sinusoidal2d ───────────────────────────────────────────────────

@register_process(
    name="simulate.sinusoidal2d",
    label="Sinusoidal Waves 2D",
    category="Simulate",
    schema=ProcessSchema(
        inputs=[],
        params=[
            _SIZE_PARAM,
            ParameterSpec(name="n_waves", type=int, default=1, label="# waves",
                          description="Number of plane waves to superpose (1–3).",
                          min=1, max=3),
            # Wave 1
            ParameterSpec(name="qx1",    type=float, default=4.0,  label="Wave 1 qx",
                          description="x wave-vector component of wave 1 (pixels, relative to size)."),
            ParameterSpec(name="qy1",    type=float, default=0.0,  label="Wave 1 qy",
                          description="y wave-vector component of wave 1."),
            ParameterSpec(name="phase1", type=float, default=0.0,  label="Wave 1 phase (rad)",
                          description="Phase of wave 1 in radians."),
            # Wave 2
            ParameterSpec(name="qx2",    type=float, default=0.0,  label="Wave 2 qx"),
            ParameterSpec(name="qy2",    type=float, default=4.0,  label="Wave 2 qy"),
            ParameterSpec(name="phase2", type=float, default=0.0,  label="Wave 2 phase (rad)"),
            # Wave 3
            ParameterSpec(name="qx3",    type=float, default=4.0,  label="Wave 3 qx"),
            ParameterSpec(name="qy3",    type=float, default=4.0,  label="Wave 3 qy"),
            ParameterSpec(name="phase3", type=float, default=0.0,  label="Wave 3 phase (rad)"),
        ],
    ),
    description=(
        "Superpose up to 3 sinusoidal plane waves: "
        "cos(2π(qx·X + qy·Y)/size − phase). "
        "n_waves controls how many are summed."
    ),
)
def sinusoidal2d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    size    = params["size"]
    n_waves = params["n_waves"]
    data = _sinusoidal2d(size, params["qx1"], params["qy1"], params["phase1"])
    if n_waves >= 2:
        data += _sinusoidal2d(size, params["qx2"], params["qy2"], params["phase2"])
    if n_waves >= 3:
        data += _sinusoidal2d(size, params["qx3"], params["qy3"], params["phase3"])
    return _wrap(data, "sim_sinusoidal2d")


# ─── simulate.perfect_lattice2d ──────────────────────────────────────────────

@register_process(
    name="simulate.perfect_lattice2d",
    label="Perfect Lattice 2D",
    category="Simulate",
    schema=ProcessSchema(
        inputs=[],
        params=_LATTICE_PARAMS + [
            ParameterSpec(name="p1", type=float, default=1.0, label="Phase mod p1",
                          description="Sub-lattice phase modulation period along a1 (unit cells)."),
            ParameterSpec(name="p2", type=float, default=1.0, label="Phase mod p2",
                          description="Sub-lattice phase modulation period along a2 (unit cells)."),
        ],
    ),
    description="Simulate a perfect Gaussian-atom lattice with arbitrary lattice vectors.",
)
def perfect_lattice2d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    p = params
    lattice = _GenerateLattice2D(
        p["m"], p["n"],
        p["a1x"], p["a1y"], p["a2x"], p["a2y"],
        p["Ox"], p["Oy"],
    )
    atom_size = p["atom_size"] if p["atom_size"] > 0 else None
    data = lattice.generate(atom_size, p["p1"], p["p2"])
    return _wrap(data, "sim_perfect_lattice2d")


# ─── simulate.lattice2d_line_domain_wall ─────────────────────────────────────

@register_process(
    name="simulate.lattice2d_line_domain_wall",
    label="Lattice 2D — Line Domain Wall",
    category="Simulate",
    schema=ProcessSchema(
        inputs=[],
        params=_LATTICE_PARAMS + [
            ParameterSpec(name="shift_distance", type=float, default=0.25,
                          label="Shift distance (frac.)",
                          description="Fractional shift (in units of min lattice spacing) "
                                      "applied to atoms past the image midpoint.",
                          min=0.0, max=1.0),
        ],
    ),
    description=(
        "Gaussian-atom lattice with a line domain wall at the image midpoint: "
        "atoms on the right side are shifted by shift_distance × min(|a1|,|a2|)."
    ),
)
def lattice2d_line_domain_wall(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    p = params
    lattice = _GenerateLattice2D(
        p["m"], p["n"],
        p["a1x"], p["a1y"], p["a2x"], p["a2y"],
        p["Ox"], p["Oy"],
    )
    lattice.set_displacement_line_domain_wall(p["shift_distance"])
    atom_size = p["atom_size"] if p["atom_size"] > 0 else None
    data = lattice.generate(atom_size)
    return _wrap(data, "sim_lattice2d_ldw")


# ─── simulate.lattice2d_periodic_distortion ──────────────────────────────────

@register_process(
    name="simulate.lattice2d_periodic_distortion",
    label="Lattice 2D — Periodic Distortion",
    category="Simulate",
    schema=ProcessSchema(
        inputs=[],
        params=_LATTICE_PARAMS + [
            ParameterSpec(name="d1x",   type=float, default=200.0, label="d1x (px)",
                          description="x period of the distortion wave along a1 (pixels). 0 = no modulation."),
            ParameterSpec(name="d1y",   type=float, default=0.0,   label="d1y (px)",
                          description="y period of the distortion wave along a1 (pixels). 0 = no modulation."),
            ParameterSpec(name="d2x",   type=float, default=0.0,   label="d2x (px)",
                          description="x period of the distortion wave along a2 (pixels). 0 = no modulation."),
            ParameterSpec(name="d2y",   type=float, default=200.0, label="d2y (px)",
                          description="y period of the distortion wave along a2 (pixels). 0 = no modulation."),
            ParameterSpec(name="dp_a1", type=float, default=0.1,   label="Amplitude 1 (frac.)",
                          description="Distortion amplitude for wave 1 as a fraction of |a1|."),
            ParameterSpec(name="dp_a2", type=float, default=0.1,   label="Amplitude 2 (frac.)",
                          description="Distortion amplitude for wave 2 as a fraction of |a2|."),
            ParameterSpec(name="dphi1", type=float, default=0.0,   label="Phase 1 (rad)",
                          description="Phase of distortion wave 1 in radians."),
            ParameterSpec(name="dphi2", type=float, default=0.0,   label="Phase 2 (rad)",
                          description="Phase of distortion wave 2 in radians."),
        ],
    ),
    description=(
        "Gaussian-atom lattice with a periodic (CDW-like) displacement field. "
        "d1x/d1y and d2x/d2y set the modulation periods; dp_a1/dp_a2 set the amplitude."
    ),
)
def lattice2d_periodic_distortion(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    p = params
    lattice = _GenerateLattice2D(
        p["m"], p["n"],
        p["a1x"], p["a1y"], p["a2x"], p["a2y"],
        p["Ox"], p["Oy"],
    )
    lattice.set_displacement_periodic(
        p["d1x"], p["d1y"], p["d2x"], p["d2y"],
        p["dp_a1"], p["dp_a2"], p["dphi1"], p["dphi2"],
    )
    atom_size = p["atom_size"] if p["atom_size"] > 0 else None
    data = lattice.generate(atom_size)
    return _wrap(data, "sim_lattice2d_pd")
