# -*- coding: utf-8 -*-
"""Coherence-peak width mapping with model-free and line-shape estimators."""

from __future__ import annotations

import copy
import itertools

import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import peak_prominences, peak_widths
from scipy.special import voigt_profile

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

from .gap_map import _energy_value_range_to_indices


HALF_PROMINENCE = "Half-prominence"
GAUSSIAN = "Gaussian"
LORENTZIAN = "Lorentzian"
VOIGT = "Voigt"
WIDTH_METHODS = [HALF_PROMINENCE, GAUSSIAN, LORENTZIAN, VOIGT]

_MINIMUM_POINTS = {
    HALF_PROMINENCE: 5,
    GAUSSIAN: 6,
    LORENTZIAN: 6,
    VOIGT: 7,
}

_OUT_WIDTH = [
    OutputSpec(
        type_id="uds",
        ndim=3,
        label="Coherence Peak Width Map",
        description="Coherence-peak FWHM map (1 × H × W).",
    ),
    OutputSpec(
        type_id="uds",
        ndim=3,
        label="Peak Quality Map",
        description=(
            "Method-dependent peak quality from 0 to 1 (1 × H × W)."
        ),
    ),
]


def _edge_baseline(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Return a linear edge baseline and its intercept/slope in x coordinates."""
    edge_count = max(2, min(5, x.size // 4))
    edge_indices = np.r_[0:edge_count, x.size - edge_count:x.size]
    slope, intercept = np.polyfit(x[edge_indices], y[edge_indices], 1)
    return intercept + slope * x, float(intercept), float(slope)


def _noise_sigma(values: np.ndarray) -> float:
    """Robust noise estimate from first differences."""
    differences = np.diff(values)
    if differences.size == 0:
        return 0.0
    center = np.median(differences)
    mad = np.median(np.abs(differences - center))
    return float(1.4826 * mad / np.sqrt(2.0))


def _half_prominence_width(
    energy: np.ndarray,
    signal: np.ndarray,
) -> tuple[float, float]:
    """Return interpolated half-prominence width and a 0–1 SNR quality."""
    baseline, _intercept, _slope = _edge_baseline(energy, signal)
    corrected = signal - baseline
    peak_index = int(np.argmax(corrected))
    if peak_index == 0 or peak_index == corrected.size - 1:
        return 0.0, 0.0

    prominence = float(peak_prominences(corrected, [peak_index])[0][0])
    floor = np.finfo(np.float64).eps * max(1.0, float(np.max(np.abs(signal))))
    if not np.isfinite(prominence) or prominence <= floor:
        return 0.0, 0.0

    _sample_width, _height, left_ips, right_ips = peak_widths(
        corrected, [peak_index], rel_height=0.5)
    left_ip = float(left_ips[0])
    right_ip = float(right_ips[0])
    if left_ip <= 0.0 or right_ip >= corrected.size - 1:
        return 0.0, 0.0

    sample_positions = np.arange(energy.size, dtype=np.float64)
    left_energy = float(np.interp(left_ip, sample_positions, energy))
    right_energy = float(np.interp(right_ip, sample_positions, energy))
    width = right_energy - left_energy
    if not np.isfinite(width) or width <= 0.0:
        return 0.0, 0.0

    noise = _noise_sigma(corrected)
    if noise <= floor:
        quality = 1.0
    else:
        snr = prominence / noise
        quality = snr / (snr + 1.0)
    return width, float(np.clip(quality, 0.0, 1.0))


def _gaussian_model(
    x: np.ndarray,
    intercept: float,
    slope: float,
    amplitude: float,
    center: float,
    fwhm: float,
) -> np.ndarray:
    return (intercept + slope * x
            + amplitude * np.exp(-4.0 * np.log(2.0)
                                 * ((x - center) / fwhm) ** 2))


def _lorentzian_model(
    x: np.ndarray,
    intercept: float,
    slope: float,
    amplitude: float,
    center: float,
    fwhm: float,
) -> np.ndarray:
    return (intercept + slope * x
            + amplitude / (1.0 + 4.0 * ((x - center) / fwhm) ** 2))


def _voigt_model(
    x: np.ndarray,
    intercept: float,
    slope: float,
    amplitude: float,
    center: float,
    sigma: float,
    gamma: float,
) -> np.ndarray:
    profile = voigt_profile(x - center, sigma, gamma)
    peak = float(voigt_profile(0.0, sigma, gamma))
    return intercept + slope * x + amplitude * profile / peak


def _voigt_fwhm(sigma: float, gamma: float) -> float:
    """Olivero-Longbothum approximation for the Voigt FWHM."""
    gaussian_fwhm = 2.0 * np.sqrt(2.0 * np.log(2.0)) * sigma
    lorentzian_fwhm = 2.0 * gamma
    return float(
        0.5346 * lorentzian_fwhm
        + np.sqrt(0.2166 * lorentzian_fwhm ** 2 + gaussian_fwhm ** 2)
    )


def _line_shape_width(
    energy: np.ndarray,
    signal: np.ndarray,
    method: str,
) -> tuple[float, float]:
    """Fit one line shape and return its FWHM and clipped R² quality."""
    midpoint = 0.5 * (float(energy[0]) + float(energy[-1]))
    energy_scale = 0.5 * (float(energy[-1]) - float(energy[0]))
    if energy_scale <= 0.0:
        return 0.0, 0.0
    x = (energy - midpoint) / energy_scale

    signal_scale = float(np.max(np.abs(signal)))
    if not np.isfinite(signal_scale) or signal_scale == 0.0:
        return 0.0, 0.0
    y = signal / signal_scale
    centered = y - y.mean()
    ss_tot = float(np.dot(centered, centered))
    if ss_tot <= np.finfo(np.float64).eps * max(1, y.size) * 16.0:
        return 0.0, 0.0

    baseline, intercept, slope = _edge_baseline(x, y)
    corrected = y - baseline
    peak_index = int(np.argmax(corrected))
    if peak_index == 0 or peak_index == y.size - 1:
        return 0.0, 0.0
    amplitude = float(corrected[peak_index])
    if amplitude <= np.finfo(np.float64).eps * 16.0:
        return 0.0, 0.0
    center = float(x[peak_index])

    initial_width, _quality = _half_prominence_width(x, y)
    x_spacing = np.diff(x)
    x_spacing = x_spacing[x_spacing > 0]
    minimum_width = (float(np.min(x_spacing)) * 0.25
                     if x_spacing.size else np.finfo(np.float64).eps * 64.0)
    span = float(x[-1] - x[0])
    maximum_width = 2.0 * span
    if initial_width <= 0.0:
        initial_width = span / 4.0
    initial_width = float(np.clip(initial_width, minimum_width, maximum_width))

    try:
        if method == GAUSSIAN:
            model = _gaussian_model
            initial = [intercept, slope, amplitude, center, initial_width]
            lower = [-np.inf, -np.inf, 0.0, x[0], minimum_width]
            upper = [np.inf, np.inf, np.inf, x[-1], maximum_width]
        elif method == LORENTZIAN:
            model = _lorentzian_model
            initial = [intercept, slope, amplitude, center, initial_width]
            lower = [-np.inf, -np.inf, 0.0, x[0], minimum_width]
            upper = [np.inf, np.inf, np.inf, x[-1], maximum_width]
        elif method == VOIGT:
            model = _voigt_model
            minimum_component = max(
                minimum_width * 0.01, np.finfo(np.float64).eps * 64.0)
            initial = [
                intercept,
                slope,
                amplitude,
                center,
                max(initial_width / 2.354820045, minimum_component),
                max(initial_width / 2.0, minimum_component),
            ]
            lower = [
                -np.inf, -np.inf, 0.0, x[0],
                minimum_component, minimum_component,
            ]
            upper = [
                np.inf, np.inf, np.inf, x[-1],
                maximum_width, maximum_width,
            ]
        else:
            raise ValueError(f"Unknown coherence-peak width method: {method!r}")

        fitted, _covariance = curve_fit(
            model,
            x,
            y,
            p0=initial,
            bounds=(lower, upper),
            maxfev=20_000,
        )
        prediction = model(x, *fitted)
    except (RuntimeError, ValueError, FloatingPointError, np.linalg.LinAlgError):
        return 0.0, 0.0

    if method == VOIGT:
        width_normalized = _voigt_fwhm(float(fitted[4]), float(fitted[5]))
    else:
        width_normalized = float(fitted[4])
    center_normalized = float(fitted[3])
    if (not np.isfinite(width_normalized) or width_normalized <= 0.0
            or center_normalized - width_normalized / 2.0 < x[0]
            or center_normalized + width_normalized / 2.0 > x[-1]):
        return 0.0, 0.0

    residual = y - prediction
    ss_res = float(np.dot(residual, residual))
    quality = float(np.clip(1.0 - ss_res / ss_tot, 0.0, 1.0))
    return width_normalized * energy_scale, quality


def measure_coherence_peak_width(
    energy: np.ndarray,
    signal: np.ndarray,
    method: str = HALF_PROMINENCE,
) -> tuple[float, float]:
    """Measure one spectrum and return ``(FWHM, quality)``.

    ``quality`` is a prominence-to-noise score for Half-prominence and clipped
    R² for Gaussian, Lorentzian, and Voigt fits.
    """
    if method not in WIDTH_METHODS:
        raise ValueError(f"Unknown coherence-peak width method: {method!r}")
    energy = np.asarray(energy, dtype=np.float64)
    signal = np.asarray(signal, dtype=np.float64)
    if (energy.ndim != 1 or signal.ndim != 1 or energy.size != signal.size
            or energy.size < _MINIMUM_POINTS[method]
            or not np.all(np.isfinite(energy))
            or not np.all(np.isfinite(signal))):
        return 0.0, 0.0

    order = np.argsort(energy)
    energy = energy[order]
    signal = signal[order]
    if np.unique(energy).size != energy.size:
        return 0.0, 0.0

    signal_scale = float(np.max(np.abs(signal)))
    if not np.isfinite(signal_scale) or signal_scale == 0.0:
        return 0.0, 0.0
    normalized = signal / signal_scale
    if method == HALF_PROMINENCE:
        return _half_prominence_width(energy, normalized)
    return _line_shape_width(energy, normalized, method)


def _coherence_peak_width_core(
    data3d: np.ndarray,
    energies: np.ndarray,
    method: str,
    energy_min: float | None,
    energy_max: float | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return width and quality arrays with shape ``(1, H, W)``."""
    energies = np.asarray(energies, dtype=np.float64)
    data3d = np.asarray(data3d)
    if method not in WIDTH_METHODS:
        raise ValueError(f"Unknown coherence-peak width method: {method!r}")
    if energies.ndim != 1 or not np.all(np.isfinite(energies)):
        raise ValueError("Peak-width energies must be a finite one-dimensional array.")
    if data3d.ndim != 3 or data3d.shape[0] != energies.size:
        raise ValueError(
            "Peak-width data must have shape (energy, height, width) matching "
            "the energy axis."
        )

    start, end = _energy_value_range_to_indices(
        energies, energy_min, energy_max)
    energy = energies[start:end + 1]
    minimum_points = _MINIMUM_POINTS[method]
    if energy.size < minimum_points:
        raise ValueError(
            f"{method} width requires at least {minimum_points} energy points "
            "in the selected range."
        )
    if np.unique(energy).size != energy.size:
        raise ValueError("Peak-width energy values must be distinct.")

    height, width = data3d.shape[-2:]
    width_map = np.zeros((height, width), dtype=np.float64)
    quality_map = np.zeros((height, width), dtype=np.float64)
    for row, column in itertools.product(range(height), range(width)):
        measured_width, quality = measure_coherence_peak_width(
            energy,
            data3d[start:end + 1, row, column],
            method,
        )
        width_map[row, column] = measured_width
        quality_map[row, column] = quality
    return width_map[np.newaxis], quality_map[np.newaxis]


@register_process(
    name="spectral.coherence_peak_width_2d",
    label="Coherence Peak Width 2D",
    category="Spectroscopy & Profiles",
    schema=ProcessSchema(
        outputs=_OUT_WIDTH,
        inputs=[
            InputSpec(
                name="data",
                type_id="uds",
                label="dI/dV 3D stack",
                description="3-D dI/dV stack with energy as the layer axis.",
                ndim=3,
            ),
        ],
        params=[
            ParameterSpec(
                name="method",
                type=str,
                default=HALF_PROMINENCE,
                label="Width method",
                choices=WIDTH_METHODS,
                description=(
                    "Half-prominence is model-free; the other choices fit a "
                    "linear baseline plus the selected line shape."
                ),
            ),
            ParameterSpec(
                name="energy_min",
                type=float,
                default=None,
                label="Energy minimum",
                description=(
                    "Lower physical energy bound. The nearest recorded layer "
                    "is used."
                ),
                decimals=9,
                axis_input="data",
                axis_index=0,
                axis_default="min",
            ),
            ParameterSpec(
                name="energy_max",
                type=float,
                default=None,
                label="Energy maximum",
                description=(
                    "Upper physical energy bound. The nearest recorded layer "
                    "is used."
                ),
                decimals=9,
                axis_input="data",
                axis_index=0,
                axis_default="max",
            ),
        ],
    ),
    description=(
        "Measure coherence-peak FWHM at every pixel using half-prominence, "
        "Gaussian, Lorentzian, or Voigt estimation. Returns width and "
        "method-dependent quality maps."
    ),
)
def coherence_peak_width(inputs: dict, params: dict, *, annotations=None) -> list:
    src = inputs["data"]
    energies = src.axes[0].values.astype(np.float64)
    width_data, quality_data = _coherence_peak_width_core(
        src.data,
        energies,
        params["method"],
        params.get("energy_min"),
        params.get("energy_max"),
    )

    width_result = UdsDataStru(
        name=src.name + "_peak_width",
        data=width_data,
        axes=[
            Axis(values=np.array([0.0]), label="FWHM", units=src.axes[0].units),
            copy.deepcopy(src.axes[1]),
            copy.deepcopy(src.axes[2]),
        ],
        info=dict(src.info),
        proc_history=[copy.deepcopy(record) for record in src.proc_history],
    )
    quality_result = UdsDataStru(
        name=src.name + "_peak_quality",
        data=quality_data,
        axes=[
            Axis(values=np.array([0.0]), label="Peak quality", units=""),
            copy.deepcopy(src.axes[1]),
            copy.deepcopy(src.axes[2]),
        ],
        info=dict(src.info),
        proc_history=[copy.deepcopy(record) for record in src.proc_history],
    )
    return [width_result, quality_result]
