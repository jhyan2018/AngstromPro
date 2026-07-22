# -*- coding: utf-8 -*-
"""
FFT processes for AngstromPro.

Registered processes
--------------------
    spectral.fft2d   2-D FFT of each layer in a 3-D (bias/energy × X × Y) stack.
                     Output axes are converted to reciprocal-space (1/m, or 1/units).
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import (
    Axis,
    UdsDataStru,
    FFT_DOMAIN_KEY,
    FFT_TRANSFORM_KEY,
    FFT_SOURCE_NAME_KEY,
    FFT_WINDOW_KEY,
    FFT_TUKEY_ALPHA_KEY,
)
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_WINDOW_CHOICES = ["none", "hann", "hamming", "tukey", "blackman", "blackman-harris"]

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

_SCHEMA_FFT2D = ProcessSchema(
    outputs=_OUT_3D,
    inputs=[
        InputSpec(
            name        = "data",
            type_id     = "uds",
            label       = "3D Stack",
            description = "UdsDataStru with ndim=3 (layers × rows × cols).",
            ndim        = 3,
        ),
    ],
    params=[
        ParameterSpec(
            name        = "window",
            type        = str,
            default     = "none",
            label       = "Window",
            description = "2-D window applied before FFT to reduce spectral leakage.",
            choices     = _WINDOW_CHOICES,
        ),
        ParameterSpec(
            name        = "tukey_alpha",
            type        = float,
            default     = 0.5,
            label       = "Tukey α",
            description = "Taper fraction for Tukey window (0 = rectangular, 1 = Hann). Only used when Window = tukey.",
            min         = 0.0,
            max         = 1.0,
            step        = 0.05,
        ),
        ParameterSpec(
            name        = "normalized",
            type        = bool,
            default     = True,
            label       = "Normalize",
            description = "Divide each FFT by N_rows × N_cols.",
        ),
    ],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_2d_window(name: str, n_rows: int, n_cols: int, tukey_alpha: float) -> np.ndarray:
    """
    Build a 2-D separable window by outer-producting two 1-D windows.
    Returns an (n_rows × n_cols) float64 array normalised to max = 1.
    """
    if name in {"tukey", "blackman", "blackman-harris"}:
        # SciPy is substantial; load it only when its windows are requested.
        from scipy.signal.windows import tukey, blackman, blackmanharris

    def _1d(n: int) -> np.ndarray:
        if name == "none":
            return np.ones(n)
        if name == "hann":
            return np.hanning(n)
        if name == "hamming":
            return np.hamming(n)
        if name == "tukey":
            return tukey(n, alpha=tukey_alpha)
        if name == "blackman":
            return blackman(n)
        if name == "blackman-harris":
            return blackmanharris(n)
        return np.ones(n)

    wr = _1d(n_rows)
    wc = _1d(n_cols)
    return np.outer(wr, wc)


def _reciprocal_axis(spatial_axis: Axis) -> Axis:
    """
    Build a frequency-space Axis from a real-space spatial Axis.

    The spatial axis is assumed to have uniform spacing d.  The output
    axis covers [-1/(2d), +1/(2d)] with N points (matching fftshift output).
    Units become '1/<original_units>' (e.g. '1/m').
    """
    v = spatial_axis.values
    n = len(v)
    d = float(v[1] - v[0]) if n > 1 else 1.0
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=d))
    orig_units = spatial_axis.units or "m"
    k_units = f"1/{orig_units}"
    k_label = f"k_{spatial_axis.label}" if spatial_axis.label else "k"
    return Axis(values=freqs, label=k_label, units=k_units)


# ---------------------------------------------------------------------------
# Registered process
# ---------------------------------------------------------------------------

@register_process(
    name        = "spectral.fft_2d",
    label       = "FFT 2D",
    category    = "Fourier & Wavevector",
    schema      = _SCHEMA_FFT2D,
    description = "Apply 2-D FFT to every layer of a 3-D bias/energy stack.",
)
def fft2d(inputs: dict, params: dict, *, annotations: dict | None = None) -> UdsDataStru:
    """
    Apply np.fft.fft2 + fftshift to each layer (axis-0 slice) of a 3-D stack.

    The spatial axes (1 and 2) are replaced by their reciprocal-space equivalents.
    The layer axis (axis 0, e.g. bias/energy) is preserved unchanged.
    Output dtype is complex128.

    Parameters
    ----------
    inputs["data"] : UdsDataStru   ndim must be 3.
    params["normalized"] : bool    If True, divide by N_rows × N_cols.
    """
    src: UdsDataStru = inputs["data"]

    if src.data.ndim != 3:
        raise ValueError(
            f"spectral.fft_2d requires a 3-D array (layers × rows × cols); "
            f"got shape {src.data.shape}."
        )
    if len(src.axes) < 3:
        raise ValueError(
            f"spectral.fft_2d requires at least 3 axes; got {len(src.axes)}."
        )

    window_name  = params["window"]
    tukey_alpha  = float(params["tukey_alpha"])
    normalized   = params["normalized"]
    n_layers, n_rows, n_cols = src.data.shape
    norm_factor  = (n_rows * n_cols) if normalized else 1

    win2d = _make_2d_window(window_name, n_rows, n_cols, tukey_alpha)

    # --- FFT per layer -------------------------------------------------------
    out = np.empty_like(src.data, dtype=np.complex128)
    for i in range(n_layers):
        out[i] = np.fft.fftshift(np.fft.fft2(src.data[i] * win2d)) / norm_factor

    # --- Axes ----------------------------------------------------------------
    layer_axis = copy.deepcopy(src.axes[0])           # bias/energy unchanged
    k_axis_x   = _reciprocal_axis(src.axes[1])
    k_axis_y   = _reciprocal_axis(src.axes[2])
    extra_axes  = [copy.deepcopy(ax) for ax in src.axes[3:]]

    info = dict(src.info)
    info.update({
        FFT_DOMAIN_KEY: "reciprocal",
        FFT_TRANSFORM_KEY: "fft_2d",
        FFT_SOURCE_NAME_KEY: src.name,
        FFT_WINDOW_KEY: window_name,
        FFT_TUKEY_ALPHA_KEY: tukey_alpha,
    })

    return UdsDataStru(
        name         = src.name + "_fft",
        data         = out,
        axes         = [layer_axis, k_axis_x, k_axis_y, *extra_axes],
        info         = info,
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
