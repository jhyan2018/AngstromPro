# -*- coding: utf-8 -*-
"""Spatially average an image stack into a spectrum and its uncertainty."""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)


STANDARD_DEVIATION = "Standard deviation"
STANDARD_ERROR = "Standard error"
ERROR_QUANTITIES = [STANDARD_DEVIATION, STANDARD_ERROR]


_OUT_AVERAGE_SPECTRUM = [
    OutputSpec(
        type_id="uds",
        ndim=2,
        label="Average Spectrum",
        description="Spatial mean as a one-curve UDS (1 × energy points).",
    ),
    OutputSpec(
        type_id="uds",
        ndim=2,
        label="Average Spectrum Error",
        description=(
            "Selected spatial error quantity, shape-matched to the average "
            "spectrum for use as symmetric Y-error data."
        ),
    ),
]


def _average_spectrum_core(
    data3d: np.ndarray,
    error_quantity: str = STANDARD_DEVIATION,
) -> tuple[np.ndarray, np.ndarray]:
    """Return spatial mean and selected error with shape ``(1, layers)``."""
    data = np.asarray(data3d)
    if data.ndim != 3:
        raise ValueError(
            "Average Spectrum 2D requires data shaped "
            "(energy, rows, columns)."
        )
    if data.shape[0] == 0 or data.shape[1] == 0 or data.shape[2] == 0:
        raise ValueError("Average Spectrum 2D requires a non-empty image stack.")
    if np.iscomplexobj(data):
        raise ValueError(
            "Average Spectrum 2D requires real-valued data because a symmetric "
            "Y error is not defined for complex spectra."
        )

    values = data.astype(np.float64, copy=False)
    if not np.all(np.isfinite(values)):
        raise ValueError("Average Spectrum 2D requires finite data values.")
    if error_quantity not in ERROR_QUANTITIES:
        raise ValueError(
            f"Unknown Average Spectrum 2D error quantity: {error_quantity!r}.")

    samples = values.reshape(values.shape[0], -1)
    mean = samples.mean(axis=1)
    if samples.shape[1] == 1:
        error = np.zeros_like(mean)
    else:
        error = samples.std(axis=1, ddof=1)
        if error_quantity == STANDARD_ERROR:
            error = error / np.sqrt(samples.shape[1])

    return mean[np.newaxis], error[np.newaxis]


@register_process(
    name="spectral.average_spectrum_2d",
    label="Average Spectrum 2D",
    category="Spectroscopy & Profiles",
    schema=ProcessSchema(
        outputs=_OUT_AVERAGE_SPECTRUM,
        inputs=[
            InputSpec(
                name="data",
                type_id="uds",
                label="Spectroscopy image stack",
                description=(
                    "3-D UDS shaped (energy, rows, columns), with energy on "
                    "axis[0]."
                ),
                ndim=3,
            ),
        ],
        params=[
            ParameterSpec(
                name="error_quantity",
                type=str,
                default=STANDARD_DEVIATION,
                label="Error quantity",
                choices=ERROR_QUANTITIES,
                description=(
                    "Standard deviation shows spatial variation between "
                    "spectra. Standard error estimates uncertainty in the "
                    "spatial mean and decreases as 1/sqrt(pixel count)."
                ),
            ),
        ],
    ),
    description=(
        "Average every spatial pixel over axes 1 and 2 for each energy. "
        "Returns the average spectrum and the selected spatial error quantity "
        "as two shape-matched curve-stack UDS items."
    ),
)
def average_spectrum(inputs: dict, params: dict, *, annotations=None) -> list[UdsDataStru]:
    src = inputs["data"]
    if len(src.axes) < 1 or len(src.axes[0].values) != src.data.shape[0]:
        raise ValueError(
            "spectral.average_spectrum_2d requires axis[0] to match the "
            "energy dimension."
        )

    error_quantity = params["error_quantity"]
    average_data, error_data = _average_spectrum_core(src.data, error_quantity)
    curve_axis = Axis(
        values=np.array([0.0]),
        label="Spatial mean",
        units="",
        axis_type=AxisType.INDEX,
    )
    energy_axis = copy.deepcopy(src.axes[0])
    common = {
        "info": copy.deepcopy(src.info),
        "proc_history": [copy.deepcopy(record) for record in src.proc_history],
    }

    average = UdsDataStru(
        name=src.name + "_avg",
        data=average_data,
        axes=[copy.deepcopy(curve_axis), copy.deepcopy(energy_axis)],
        **common,
    )
    error_suffix = "_std" if error_quantity == STANDARD_DEVIATION else "_sem"
    error_result = UdsDataStru(
        name=src.name + "_avg" + error_suffix,
        data=error_data,
        axes=[copy.deepcopy(curve_axis), copy.deepcopy(energy_axis)],
        info=copy.deepcopy(src.info),
        proc_history=[copy.deepcopy(record) for record in src.proc_history],
    )
    return [average, error_result]
