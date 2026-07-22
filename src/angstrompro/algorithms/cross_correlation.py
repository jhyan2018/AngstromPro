# -*- coding: utf-8 -*-
"""
Cross-correlation processes for AngstromPro.

Registered processes
--------------------
    math.cross_correlation
        Normalised 2-D spatial cross-correlation between one layer of two
        stacks.  Uses scipy.signal.correlate (mode='same') after mean
        subtraction.  Output is a single-layer UDS the same spatial size
        as the inputs.  Name suffix: _xcorr

    math.statistic_cross_correlation
        Intensity-intensity 2-D histogram between one layer of two stacks.
        Counts co-occurrences of pixel intensities within ±sigma standard
        deviations of the mean, binned into a size×size grid.
        Output is a single-layer UDS of shape (size, size); axes carry the
        intensity range of each stack.  Name suffix: _sxcorr
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

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

_TWO_STACK_INPUTS = [
    InputSpec(
        name        = "data_a",
        type_id     = "uds",
        label       = "Stack A",
        description = "Primary 3-D stack (main).",
        ndim        = 3,
    ),
    InputSpec(
        name        = "data_b",
        type_id     = "uds",
        label       = "Stack B",
        description = "Secondary 3-D stack (reference/slave).",
        ndim        = 3,
    ),
]

_LAYER_PARAM = ParameterSpec(
    name        = "layer_index",
    type        = int,
    default     = 0,
    label       = "Layer index",
    description = "Which layer of each stack to use for the correlation (0 = first).",
    min         = 0,
)


# ---------------------------------------------------------------------------
# math.cross_correlation
# ---------------------------------------------------------------------------

@register_process(
    name        = "math.cross_correlation_2d",
    label       = "Cross Correlation 2D",
    category    = "Correlation & Statistics",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs = _TWO_STACK_INPUTS,
        params = [_LAYER_PARAM],
    ),
    description = (
        "Normalised 2-D spatial cross-correlation between one layer of two stacks. "
        "Mean-subtracted before correlation; output is normalised to [-1, 1]."
    ),
)
def cross_correlation(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    from scipy.signal import correlate

    a   = inputs["data_a"]
    b   = inputs["data_b"]
    idx = params["layer_index"]

    da = a.data[idx].astype(np.float64)
    db = b.data[idx].astype(np.float64)

    da -= da.mean()
    db -= db.mean()

    xcorr = correlate(da, db, mode="same")
    norm  = np.sqrt((da ** 2).sum() * (db ** 2).sum())
    if norm > 0:
        xcorr /= norm

    out = xcorr[np.newaxis]

    return UdsDataStru(
        name         = a.name + "_xcorr",
        data         = out,
        axes         = [Axis(values=np.array([0.0]), label="Layer", units=""),
                        copy.deepcopy(a.axes[1]),
                        copy.deepcopy(a.axes[2])],
        info         = dict(a.info),
        proc_history = [copy.deepcopy(r) for r in a.proc_history],
    )


# ---------------------------------------------------------------------------
# math.statistic_cross_correlation
# ---------------------------------------------------------------------------

def _statistic_cross_correlation(da: np.ndarray, db: np.ndarray,
                                  size: int, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (histogram, a_axis_values, b_axis_values).

    histogram shape: (size, size)
    Row 0 = highest b intensity (origin at bottom-left matches original).
    a_axis_values: centre intensity of each column bin (A intensity, horizontal).
    b_axis_values: centre intensity of each row bin (B intensity, vertical, ascending).
    """
    mu_a, sig_a = da.mean(), da.std()
    mu_b, sig_b = db.mean(), db.std()

    a_min, a_step = mu_a - sigma * sig_a, 2 * sigma * sig_a / size
    b_min, b_step = mu_b - sigma * sig_b, 2 * sigma * sig_b / size

    hist = np.zeros((size, size), dtype=np.float64)

    a_idx = ((da - a_min) / a_step).astype(int)
    b_idx = ((db - b_min) / b_step).astype(int)

    mask = (a_idx >= 0) & (a_idx < size) & (b_idx >= 0) & (b_idx < size)
    for ai, bi in zip(a_idx[mask].ravel(), b_idx[mask].ravel()):
        hist[size - bi - 1, ai] += 1   # origin at bottom-left

    a_axis = a_min + (np.arange(size) + 0.5) * a_step
    b_axis = b_min + (np.arange(size) + 0.5) * b_step   # ascending

    return hist, a_axis, b_axis


@register_process(
    name        = "math.statistic_cross_correlation_2d",
    label       = "Statistic Cross Correlation 2D",
    category    = "Correlation & Statistics",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs = _TWO_STACK_INPUTS,
        params = [
            _LAYER_PARAM,
            ParameterSpec(
                name        = "size",
                type        = int,
                default     = 100,
                label       = "Histogram size (px)",
                description = "Number of bins along each intensity axis; output is size×size.",
                min         = 10,
                max         = 1024,
            ),
            ParameterSpec(
                name        = "sigma",
                type        = float,
                default     = 3.0,
                label       = "Sigma range",
                description = "Data within ±sigma standard deviations of the mean are included. "
                              "Pixels outside this range are ignored.",
                min         = 0.1,
                max         = 10.0,
            ),
        ],
    ),
    description = (
        "2-D intensity-intensity histogram between one layer of two stacks. "
        "Horizontal axis = intensity of Stack A; vertical axis = intensity of Stack B. "
        "Only pixels within ±sigma std devs of each mean are counted."
    ),
)
def statistic_cross_correlation(inputs: dict, params: dict,
                                *, annotations=None) -> UdsDataStru:
    a    = inputs["data_a"]
    b    = inputs["data_b"]
    idx  = params["layer_index"]
    size = params["size"]
    sig  = params["sigma"]

    da = a.data[idx].astype(np.float64)
    db = b.data[idx].astype(np.float64)

    hist, a_axis, b_axis = _statistic_cross_correlation(da, db, size, sig)

    return UdsDataStru(
        name         = a.name + "_sxcorr",
        data         = hist[np.newaxis],
        axes         = [
            Axis(values=np.array([0.0]),  label="Layer",            units=""),
            Axis(values=b_axis[::-1],     label=b.name + " intensity",  units=""),
            Axis(values=a_axis,           label=a.name + " intensity",  units=""),
        ],
        info         = dict(a.info),
        proc_history = [copy.deepcopy(r) for r in a.proc_history],
    )
