# -*- coding: utf-8 -*-
"""
FFT processes for AngstromPro.

Registered processes
--------------------
    spectral.fft_1d  1-D FFT of every row in a 2-D curve stack.
    spectral.fft_2d  2-D FFT of each layer in a 3-D (bias/energy × X × Y) stack.
                     Transformed axes are converted to reciprocal-frequency units.
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import (
    Axis,
    AxisType,
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
_OUT_2D = [OutputSpec(
    type_id="uds",
    ndim=2,
    label="Curve Stack",
    description="Complex ndim=2 UDS (curves × reciprocal-frequency points).",
)]


def _window_params(description: str) -> list[ParameterSpec]:
    return [
        ParameterSpec(
            name="window",
            type=str,
            default="none",
            label="Window",
            description=description,
            choices=_WINDOW_CHOICES,
        ),
        ParameterSpec(
            name="tukey_alpha",
            type=float,
            default=0.5,
            label="Tukey α",
            description=(
                "Taper fraction for Tukey window (0 = rectangular, 1 = "
                "Hann). Only used when Window = tukey."
            ),
            min=0.0,
            max=1.0,
            step=0.05,
        ),
    ]


_SCHEMA_FFT1D = ProcessSchema(
    outputs=_OUT_2D,
    inputs=[
        InputSpec(
            name="data",
            type_id="uds",
            label="Curve Stack",
            description="UdsDataStru with ndim=2 (curves × points).",
            ndim=2,
        ),
    ],
    params=[
        *_window_params(
            "1-D window applied independently to every curve before FFT to "
            "reduce spectral leakage."
        ),
        ParameterSpec(
            name="normalized",
            type=bool,
            default=True,
            label="Normalize",
            description="Divide each FFT by the number of points.",
        ),
    ],
)

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
        *_window_params(
            "2-D window applied before FFT to reduce spectral leakage."
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

def _make_1d_window(name: str, size: int, tukey_alpha: float) -> np.ndarray:
    """Build one supported 1-D FFT window."""
    if name == "none":
        window = np.ones(size)
    elif name == "hann":
        window = np.hanning(size)
    elif name == "hamming":
        window = np.hamming(size)
    elif name in {"tukey", "blackman", "blackman-harris"}:
        # SciPy is substantial; load it only when its windows are requested.
        from scipy.signal.windows import tukey, blackman, blackmanharris

        if name == "tukey":
            window = tukey(size, alpha=tukey_alpha)
        elif name == "blackman":
            window = blackman(size)
        else:
            window = blackmanharris(size)
    else:
        raise ValueError(f"Unknown FFT window: {name!r}.")
    return window


def _make_2d_window(name: str, n_rows: int, n_cols: int, tukey_alpha: float) -> np.ndarray:
    """
    Build a 2-D separable window by outer-producting two 1-D windows.
    Returns an (n_rows × n_cols) float64 array.
    """
    wr = _make_1d_window(name, n_rows, tukey_alpha)
    wc = _make_1d_window(name, n_cols, tukey_alpha)
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


def _frequency_axis(sample_axis: Axis) -> Axis:
    """Build the FFT-conjugate axis for a uniformly sampled curve axis."""
    values = np.asarray(sample_axis.values, dtype=float)
    size = len(values)
    if size == 0:
        raise ValueError("FFT 1D requires a non-empty sample axis.")
    spacing = float(values[1] - values[0]) if size > 1 else 1.0
    if spacing == 0.0 or not np.isfinite(spacing):
        raise ValueError("FFT 1D requires a finite, non-zero axis spacing.")
    if size > 2 and not np.allclose(
            np.diff(values), spacing, rtol=1e-7, atol=1e-12):
        raise ValueError("FFT 1D requires a uniformly sampled curve axis.")
    frequencies = np.fft.fftshift(np.fft.fftfreq(size, d=spacing))
    original_label = str(sample_axis.label or "").strip()
    original_units = str(sample_axis.units or "").strip()
    frequency_units = (
        "Hz" if original_units == "s"
        else f"1/{original_units}" if original_units
        else "cycles/sample"
    )
    return Axis(
        values=frequencies,
        label=f"f_{original_label}" if original_label else "Frequency",
        units=frequency_units,
        axis_type=AxisType.FREQUENCY,
    )


# ---------------------------------------------------------------------------
# Registered process
# ---------------------------------------------------------------------------

@register_process(
    name="spectral.fft_1d",
    label="FFT 1D",
    category="Fourier & Wavevector",
    schema=_SCHEMA_FFT1D,
    description=(
        "Apply a 1-D FFT independently to every curve in a curve stack."
    ),
)
def fft1d(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    """Apply a shifted 1-D FFT along the last axis of an ndim=2 UDS."""
    src: UdsDataStru = inputs["data"]
    data = np.asarray(src.data)
    if data.ndim != 2:
        raise ValueError(
            "spectral.fft_1d requires a 2-D array (curves × points); "
            f"got shape {data.shape}."
        )
    if len(src.axes) < 2:
        raise ValueError(
            f"spectral.fft_1d requires at least 2 axes; got {len(src.axes)}."
        )
    if len(src.axes[1].values) != data.shape[1]:
        raise ValueError(
            "spectral.fft_1d requires axis[1] to match the point dimension."
        )

    window_name = str(params["window"])
    tukey_alpha = float(params["tukey_alpha"])
    normalized = bool(params["normalized"])
    point_count = data.shape[1]
    window = _make_1d_window(window_name, point_count, tukey_alpha)
    norm_factor = point_count if normalized else 1
    frequency_axis = _frequency_axis(src.axes[1])
    transformed = np.fft.fftshift(
        np.fft.fft(data * window[np.newaxis, :], axis=-1), axes=-1
    ) / norm_factor

    info = copy.deepcopy(src.info)
    info.update({
        FFT_DOMAIN_KEY: "frequency",
        FFT_TRANSFORM_KEY: "fft_1d",
        FFT_SOURCE_NAME_KEY: src.name,
        FFT_WINDOW_KEY: window_name,
        FFT_TUKEY_ALPHA_KEY: tukey_alpha,
    })
    return UdsDataStru(
        name=src.name + "_fft",
        data=np.asarray(transformed, dtype=np.complex128),
        axes=[
            copy.deepcopy(src.axes[0]),
            frequency_axis,
            *[copy.deepcopy(axis) for axis in src.axes[2:]],
        ],
        info=info,
        proc_history=[copy.deepcopy(record) for record in src.proc_history],
    )

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
