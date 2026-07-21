# -*- coding: utf-8 -*-
"""
FFT filter processes for AngstromPro.

Both processes operate on a real-space 3-D UdsDataStru and require
filter_points annotations stored on that item (picked on the FFT/aux panel
via Points → "Set Filter Points from Aux").

The FFT is computed internally — callers do not need to pass the FFT item.

Registered processes
--------------------
    spectral.fft_filter_isolate
        Isolate the real-space signal at picked k-points:
        FFT → Gaussian window around each point → IFFT → sum.
        Name suffix: _fi.

    spectral.fft_filter_out
        Remove picked periodicities (notch filter):
        original real-space data minus the isolated signal.
        Name suffix: _fo.

Window types
------------
    GAUSSIAN   exp(-(dx²+dy²) / (2·kSigma²))
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
from angstrompro.core.processes.param_schema import AnnotationSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WINDOW_CHOICES = ["GAUSSIAN"]


def _gaussian_window(shape: tuple[int, int], cx: float, cy: float,
                     sigma: float) -> np.ndarray:
    y = np.arange(shape[0])
    x = np.arange(shape[1])
    X, Y = np.meshgrid(x, y)
    return np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * sigma ** 2))


def _filter_window(shape, cx, cy, sigma, window_type) -> np.ndarray:
    if window_type == "GAUSSIAN":
        return _gaussian_window(shape, cx, cy, sigma)
    raise ValueError(f"Unknown window type: {window_type!r}")


def _isolate_one_layer(layer_real: np.ndarray, filter_points: np.ndarray,
                       window_type: str, k_sigma: float) -> np.ndarray:
    """
    Isolate signal at picked k-points for a single real-space 2-D layer.

    Sequential approach: each peak is isolated from a working copy of the
    data that already has all previously isolated peaks subtracted.  This
    means peak N sees no residual from peak N-1, so overlapping Gaussian
    windows never cause double-counting — works correctly at any kSigma.

    Parameters
    ----------
    layer_real    : (H, W) real array — one real-space layer.
    filter_points : (N, 2) [col, row] pixel coordinates in the FFT image.
    window_type   : window function name.
    k_sigma       : half-width of the filter window in FFT pixels.

    Returns
    -------
    (H, W) float64 real-space image containing only the picked periodicities.
    """
    H, W = layer_real.shape
    origin_x = (W - W % 2) / 2
    origin_y = (H - H % 2) / 2

    accumulated = np.zeros((H, W), dtype=np.float64)
    working     = layer_real.astype(np.float64, copy=True)

    for pt in filter_points:
        px, py = float(pt[0]), float(pt[1])   # col, row

        layer_fft = np.fft.fftshift(np.fft.fft2(working))
        win = _filter_window((H, W), px, py, k_sigma, window_type)
        contribution = np.fft.ifft2(np.fft.ifftshift(layer_fft * win))

        if px == origin_x and py == origin_y:
            isolated = np.real(contribution)
        else:
            isolated = 2.0 * np.real(contribution)

        accumulated += isolated
        # working copy = original minus everything isolated so far
        working = layer_real - accumulated

    return accumulated


def _get_filter_points(annotations: dict) -> np.ndarray:
    """Extract (N, 2) [col, row] array from the filter_points annotation."""
    ann = annotations.get("filter_points")
    if ann is None or not hasattr(ann, "coords") or len(ann.coords) == 0:
        raise ValueError(
            "No filter points found. Pick points on the FFT in the aux panel "
            "and run Points → 'Set Filter Points from Aux' before running this process."
        )
    coords = np.asarray(ann.coords)   # stored as [row, col]
    return coords[:, ::-1]            # → [col, row]


def _copy_axes(src: UdsDataStru) -> list[Axis]:
    return [copy.deepcopy(ax) for ax in src.axes]


# ---------------------------------------------------------------------------
# Shared schema pieces
# ---------------------------------------------------------------------------

_SHARED_PARAMS = [
    ParameterSpec(
        name        = "window_type",
        type        = str,
        default     = "GAUSSIAN",
        label       = "Window type",
        description = "Shape of the filter window applied around each k-point.",
        choices     = _WINDOW_CHOICES,
    ),
    ParameterSpec(
        name        = "k_sigma",
        type        = float,
        default     = 3.0,
        label       = "k σ (pixels)",
        description = "Half-width of the Gaussian filter window in FFT pixels.",
        min         = 0.5,
        max         = 200.0,
        step        = 0.5,
    ),
]

_FILTER_ANNOTATION = AnnotationSpec(
    name     = "filter_points",
    role     = "filter_points",
    type_id  = "point_set",
    required = True,
)

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

_INPUT_SPEC = InputSpec(
    name        = "data",
    type_id     = "uds",
    label       = "Real-space Stack",
    description = "3-D real-space UdsDataStru with filter_points annotation.",
    ndim        = 3,
)

# ---------------------------------------------------------------------------
# spectral.fft_filter_isolate
# ---------------------------------------------------------------------------

@register_process(
    name        = "spectral.fft_filter_isolate_2d",
    label       = "FFT Filter — Isolate 2D",
    category    = "Fourier & Wavevector",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs      = [_INPUT_SPEC],
        params      = _SHARED_PARAMS,
        annotations = [_FILTER_ANNOTATION],
    ),
    description = "Isolate the real-space signal at picked FFT k-points "
                  "(Gaussian window around each point, IFFT, summed).",
)
def fft_filter_isolate(inputs: dict, params: dict,
                       *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(
            f"spectral.fft_filter_isolate_2d requires ndim=3; got {src.data.shape}.")

    filter_points = _get_filter_points(annotations or {})
    window_type   = params["window_type"]
    k_sigma       = float(params["k_sigma"])
    n_layers      = src.data.shape[0]

    out = np.empty_like(src.data, dtype=np.float64)
    for i in range(n_layers):
        out[i] = _isolate_one_layer(src.data[i], filter_points,
                                    window_type, k_sigma)

    return UdsDataStru(
        name         = src.name + "_fi",
        data         = out,
        axes         = _copy_axes(src),
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )


# ---------------------------------------------------------------------------
# spectral.fft_filter_out
# ---------------------------------------------------------------------------

@register_process(
    name        = "spectral.fft_filter_out_2d",
    label       = "FFT Filter — Notch Out 2D",
    category    = "Fourier & Wavevector",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs      = [_INPUT_SPEC],
        params      = _SHARED_PARAMS,
        annotations = [_FILTER_ANNOTATION],
    ),
    description = "Remove picked FFT periodicities from the real-space data "
                  "(original minus isolated signal — notch filter).",
)
def fft_filter_out(inputs: dict, params: dict,
                   *, annotations: dict | None = None) -> UdsDataStru:
    src: UdsDataStru = inputs["data"]
    if src.data.ndim != 3:
        raise ValueError(
            f"spectral.fft_filter_out_2d requires ndim=3; got {src.data.shape}.")

    filter_points = _get_filter_points(annotations or {})
    window_type   = params["window_type"]
    k_sigma       = float(params["k_sigma"])
    n_layers      = src.data.shape[0]

    isolated = np.empty_like(src.data, dtype=np.float64)
    for i in range(n_layers):
        isolated[i] = _isolate_one_layer(src.data[i], filter_points,
                                         window_type, k_sigma)

    return UdsDataStru(
        name         = src.name + "_fo",
        data         = src.data - isolated,
        axes         = _copy_axes(src),
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
