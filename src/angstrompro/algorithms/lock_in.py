# -*- coding: utf-8 -*-
"""
2-D lock-in mapping process for AngstromPro.

Demodulates a real-space 3-D image stack at a single wave-vector Q taken
from the first point of the ``bragg_peaks`` annotation.  All other Bragg
peaks are used to estimate the real-space lattice constant, which in turn
sets the real-space Gaussian filter width.

Physics
-------
For each layer ``f(r)``:

    A_Q(r) = IFFT{ FFT{ f(r) · e^{iQr} } · G_k(k) }

where G_k is a k-space Gaussian whose width is the Fourier-dual of the
requested real-space sigma.  The output is either:

    Amplitude map : |A_Q(r)|
    Phase map     : arg(A_Q(r))  optionally phase-unwrapped

Registered processes
--------------------
    spectral.lock_in_2d
        Produces either the amplitude or the phase map depending on the
        ``map_type`` parameter.
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
from angstrompro.core.processes.param_schema import AnnotationSpec
from .simulate import _gaussian2d

# ─── phase unwrapping ────────────────────────────────────────────────────────

def _gamma(x: np.ndarray) -> np.ndarray:
    return np.sign(x) * np.mod(np.abs(x), np.pi)


def _unwrap_phase_python(img: np.ndarray) -> np.ndarray:
    """Reliability-guided 2-D phase unwrapping (pure Python/NumPy fallback).

    Correct but slow for large images — holds the GIL during the union-find
    loop.  Only used when scikit-image is not installed.
    """
    Ny, Nx = img.shape
    rel = np.zeros_like(img)
    H  = _gamma(img[:-2, 1:-1] - img[1:-1, 1:-1]) - _gamma(img[1:-1, 1:-1] - img[2:,  1:-1])
    V  = _gamma(img[1:-1, :-2] - img[1:-1, 1:-1]) - _gamma(img[1:-1, 1:-1] - img[1:-1, 2:])
    D1 = _gamma(img[:-2, :-2]  - img[1:-1, 1:-1]) - _gamma(img[1:-1, 1:-1] - img[2:,  2:])
    D2 = _gamma(img[:-2, 2:]   - img[1:-1, 1:-1]) - _gamma(img[1:-1, 1:-1] - img[2:,  :-2])
    D  = np.sqrt(H ** 2 + V ** 2 + D1 ** 2 + D2 ** 2)
    inner = D != 0
    rel[1:-1, 1:-1][inner]  = 1.0 / D[inner]
    rel[np.isnan(img)] = np.nan

    h_edges = np.column_stack((rel[:, 1:] + rel[:, :-1], np.full((Ny, 1), np.nan)))
    v_edges = np.row_stack((rel[1:, :] + rel[:-1, :], np.full((1, Nx), np.nan)))
    edges      = np.concatenate((h_edges.ravel(), v_edges.ravel()))
    edge_bound = Ny * Nx
    sort_idx   = np.argsort(edges)[::-1]

    idxs1 = sort_idx % edge_bound
    idxs2 = np.where(sort_idx < edge_bound, idxs1 + 1, idxs1 + Nx)
    h_mask = sort_idx < edge_bound
    idxs2[h_mask & ((idxs1 % Nx) == (Nx - 1))] -= 1
    v_mask = ~h_mask
    idxs2[v_mask & ((idxs1 // Nx) == (Ny - 1))] -= Nx

    group      = np.arange(Ny * Nx).reshape(Ny, Nx)
    is_grouped = np.zeros(Ny * Nx, dtype=bool)
    members    = {i: [i] for i in range(Ny * Nx)}
    n_members  = np.ones(Ny * Nx, dtype=int)
    res        = img.copy()
    n_nan      = int(np.sum(np.isnan(edges)))

    for i in range(n_nan, len(sort_idx)):
        idx1 = idxs1[i];  idx2 = idxs2[i]
        g1 = group.ravel()[idx1];  g2 = group.ravel()[idx2]
        if g1 == g2:
            continue
        all_grouped = False
        if is_grouped[idx1]:
            if not is_grouped[idx2]:
                idx1, idx2 = idx2, idx1;  g1, g2 = g2, g1
            elif n_members[g1] > n_members[g2]:
                idx1, idx2 = idx2, idx1;  g1, g2 = g2, g1
                all_grouped = True
            else:
                all_grouped = True
        dval = np.floor((res.ravel()[idx2] - res.ravel()[idx1] + np.pi) / (2 * np.pi)) * 2 * np.pi
        pix  = members[g1] if all_grouped else [idx1]
        if dval != 0:
            res.ravel()[pix] += dval
        members[g2].extend(pix)
        group.ravel()[pix] = g2
        n_members[g2] += n_members[g1]
        is_grouped[idx1] = is_grouped[idx2] = True

    return res


def _unwrap_phase(phase: np.ndarray, method: str = "auto") -> np.ndarray:
    """2-D phase unwrapping using the Herraez reliability-guided algorithm.

    method='auto'   : try skimage first, fall back to built-in Python
    method='skimage': force skimage (ImportError raised if not installed)
    method='python' : always use built-in pure-Python implementation
    """
    if method == "python":
        return _unwrap_phase_python(phase)
    try:
        from skimage.restoration import unwrap_phase
        return unwrap_phase(phase)
    except ImportError:
        if method == "skimage":
            raise
        return _unwrap_phase_python(phase)


# ─── core lock-in computation ─────────────────────────────────────────────────

def _lock_in_layer(data2d: np.ndarray, px: float, py: float,
                   r_sigma: float) -> np.ndarray:
    """Return the complex A_Q(r) field for one layer."""
    N       = data2d.shape[-1]
    k_sigma = N / (2 * np.pi * r_sigma)
    k_factor = 2 * np.pi * r_sigma ** 2
    k_gauss = k_factor * _gaussian2d(N, k_sigma)

    O_k = (N - N % 2) / 2
    Qx  = 2 * np.pi * (px - O_k) / N
    Qy  = 2 * np.pi * (py - O_k) / N

    x = np.arange(N, dtype=np.float64)
    X, Y = np.meshgrid(x, x)
    e_qr  = np.exp(1j * (Qx * X + Qy * Y))

    A_Q_k = np.fft.fftshift(np.fft.fft2(data2d * e_qr))
    return np.fft.ifft2(np.fft.ifftshift(A_Q_k * k_gauss))


def _lattice_constant_px(coords: np.ndarray, N: int) -> float:
    """Longest real-space lattice constant (px) derived from all Bragg peaks."""
    O_k = (N - N % 2) / 2
    best = 0.0
    for pt in coords:
        row, col = float(pt[0]), float(pt[1])
        bP = np.sqrt((col - O_k) ** 2 + (row - O_k) ** 2)
        if bP > 0:
            best = max(best, N / bP)
    return best


# ─── registered process ───────────────────────────────────────────────────────

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

_SCHEMA = ProcessSchema(
    outputs=_OUT_3D,
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "Real-space 3D stack",
            description = "ndim=3 real-space image stack. "
                          "Must carry a 'bragg_peaks' annotation (PointSetData) "
                          "whose first point is the Q-vector to demodulate at.",
            ndim        = 3,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "map_type",
            type        = str,
            default     = "Amplitude",
            label       = "Map type",
            description = "Output map: amplitude |A_Q| or phase arg(A_Q).",
            choices     = ["Amplitude", "Phase"],
        ),
        ParameterSpec(
            name        = "rSigma_ref_a0",
            type        = float,
            default     = 0.5,
            label       = "σ / a₀",
            description = "Real-space Gaussian filter width expressed as a "
                          "fraction of the (longest) lattice constant. "
                          "Smaller values → better spatial resolution, "
                          "larger values → better wave-vector selectivity.",
            min         = 0.01,
            max         = 1000.0,
        ),
        ParameterSpec(
            name        = "phase_unwrap",
            type        = bool,
            default     = True,
            label       = "Phase unwrap",
            description = "Apply reliability-guided 2-D phase unwrapping "
                          "(only used when map_type='Phase').",
        ),
        ParameterSpec(
            name        = "unwrap_method",
            type        = str,
            default     = "auto",
            label       = "Unwrap method",
            description = "auto: try skimage then fall back to Python; "
                          "skimage: force skimage (must be installed); "
                          "python: built-in reliability-guided implementation.",
            choices     = ["auto", "skimage", "python"],
        ),
    ],
    annotations=[
        AnnotationSpec(
            name     = "bragg_peaks",
            role     = "bragg_peaks",
            type_id  = "point_set",
            required = True,
        ),
        AnnotationSpec(
            name     = "lockin_peak",
            role     = "lockin_peak",
            type_id  = "point_set",
            required = True,
        ),
    ],
)


@register_process(
    name        = "spectral.lock_in_2d",
    label       = "Lock-in 2D",
    category    = "Fourier & Wavevector",
    schema      = _SCHEMA,
    description = (
        "2-D lock-in mapping: demodulate the real-space image at the "
        "wave-vector Q defined by the first Bragg peak, then return either "
        "the amplitude or the (optionally unwrapped) phase map."
    ),
)
def lock_in_2d(inputs: dict, params: dict,
               *, annotations: dict | None = None) -> UdsDataStru:
    src      = inputs["data"]
    map_type = params["map_type"].strip()
    if map_type not in ("Amplitude", "Phase"):
        raise ValueError(
            f"spectral.lock_in_2d: map_type must be 'Amplitude' or 'Phase', got {map_type!r}.")

    if not annotations or "bragg_peaks" not in annotations:
        raise ValueError(
            "spectral.lock_in_2d requires a 'bragg_peaks' annotation. "
            "Pick Bragg peaks in the Aux (FFT) panel and use Points → 'Set Bragg Peaks from Aux'.")
    if "lockin_peak" not in (annotations or {}):
        raise ValueError(
            "spectral.lock_in_2d requires a 'lockin_peak' annotation. "
            "Pick one point in the Aux (FFT) panel and use Points → 'Set Lock-in Peak from Aux'.")

    bragg_coords  = annotations["bragg_peaks"].coords   # (N, 2) [row, col]
    lockin_coords = annotations["lockin_peak"].coords   # (M, 2) [row, col]
    if bragg_coords.shape[0] < 1:
        raise ValueError("spectral.lock_in_2d: 'bragg_peaks' annotation has no points.")
    if lockin_coords.shape[0] < 1:
        raise ValueError("spectral.lock_in_2d: 'lockin_peak' annotation has no points.")

    N  = src.data.shape[-1]
    px = float(lockin_coords[0, 1])   # col → x in FFT pixel coords
    py = float(lockin_coords[0, 0])   # row → y

    a0 = _lattice_constant_px(bragg_coords, N)
    if a0 <= 0:
        raise ValueError(
            "spectral.lock_in_2d: could not determine lattice constant — "
            "ensure Bragg peaks are not at the DC centre.")
    r_sigma = params["rSigma_ref_a0"] * a0

    n_layers = src.data.shape[0]
    out      = np.zeros_like(src.data, dtype=np.float64)

    for i in range(n_layers):
        A_Q_r = _lock_in_layer(src.data[i], px, py, r_sigma)
        if map_type == "Amplitude":
            out[i] = np.abs(A_Q_r)
        else:
            phase = np.arctan2(np.imag(A_Q_r), np.real(A_Q_r))
            if params["phase_unwrap"]:
                phase = _unwrap_phase(phase, params.get("unwrap_method", "auto"))
            out[i] = phase

    suffix = "_amp" if map_type == "Amplitude" else "_pha"
    return UdsDataStru(
        name         = src.name + suffix,
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
