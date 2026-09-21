from __future__ import annotations

import numpy as np
import pytest

from angstrompro.algorithms import coherence_peak_width as peak_width
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes.registry import ProcessRegistry


def _gaussian(x: np.ndarray, fwhm: float) -> np.ndarray:
    return 0.15 + 0.02 * x + np.exp(
        -4.0 * np.log(2.0) * (x / fwhm) ** 2
    )


def _lorentzian(x: np.ndarray, fwhm: float) -> np.ndarray:
    return 0.15 + 0.02 * x + 1.0 / (1.0 + 4.0 * (x / fwhm) ** 2)


@pytest.mark.parametrize(
    ("method", "signal_factory", "expected_width"),
    [
        (peak_width.HALF_PROMINENCE, lambda x: _gaussian(x, 1.2), 1.2),
        (peak_width.GAUSSIAN, lambda x: _gaussian(x, 1.2), 1.2),
        (peak_width.LORENTZIAN, lambda x: _lorentzian(x, 1.4), 1.4),
        (
            peak_width.VOIGT,
            lambda x: peak_width._voigt_model(
                x, 0.15, 0.02, 1.0, 0.0, 0.35, 0.22
            ),
            peak_width._voigt_fwhm(0.35, 0.22),
        ),
    ],
)
def test_width_methods_recover_known_fwhm(
    method: str,
    signal_factory,
    expected_width: float,
) -> None:
    energy = np.linspace(-5.0, 5.0, 401)

    width, quality = peak_width.measure_coherence_peak_width(
        energy,
        signal_factory(energy),
        method,
    )

    assert width == pytest.approx(expected_width, rel=2e-3)
    assert quality > 0.99


def test_width_core_supports_descending_axis_and_marks_invalid_pixels_zero() -> None:
    energy = np.linspace(5.0, -5.0, 201)
    data = np.empty((energy.size, 1, 3), dtype=np.float64)
    data[:, 0, 0] = _gaussian(energy, 1.5)
    data[:, 0, 1] = 0.0
    data[:, 0, 2] = 2.0

    widths, quality = peak_width._coherence_peak_width_core(
        data,
        energy,
        peak_width.GAUSSIAN,
        -4.0,
        4.0,
    )

    assert widths[0, 0, 0] == pytest.approx(1.5, rel=2e-3)
    assert quality[0, 0, 0] > 0.99
    assert np.array_equal(widths[0, 0, 1:], np.zeros(2))
    assert np.array_equal(quality[0, 0, 1:], np.zeros(2))


def test_registered_width_process_has_focused_outputs_and_provenance() -> None:
    energy = np.linspace(-4.0, 4.0, 161)
    source = UdsDataStru(
        name="didv",
        data=_gaussian(energy, 1.25)[:, np.newaxis, np.newaxis],
        axes=[
            Axis(values=energy, label="Bias", units="mV"),
            Axis(values=np.array([0.0]), label="Y", units="nm"),
            Axis(values=np.array([0.0]), label="X", units="nm"),
        ],
        info={"source": "measurement.3ds"},
    )
    registry = ProcessRegistry()
    entry = registry.get("spectral.coherence_peak_width_2d")
    method_spec = entry.schema.get_param("method")

    assert method_spec is not None
    assert method_spec.default == peak_width.HALF_PROMINENCE
    assert method_spec.choices == peak_width.WIDTH_METHODS
    assert [output.label for output in entry.schema.outputs] == [
        "Coherence Peak Width Map",
        "Peak Quality Map",
    ]

    result = registry.run(
        entry.name,
        {"data": source},
        {"method": peak_width.GAUSSIAN},
    )

    assert [item.name for item in result] == [
        "didv_peak_width",
        "didv_peak_quality",
    ]
    assert result[0].data[0, 0, 0] == pytest.approx(1.25, rel=2e-3)
    assert result[0].axes[0].units == "mV"
    for item in result:
        assert item.info["source"] == "measurement.3ds"
        assert item.proc_history[-1].step == entry.name
