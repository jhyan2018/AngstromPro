from __future__ import annotations

import numpy as np
import pytest

from angstrompro.algorithms.average_spectrum import (
    STANDARD_DEVIATION,
    STANDARD_ERROR,
    _OUT_AVERAGE_SPECTRUM,
    _average_spectrum_core,
)
from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.core.processes.registry import ProcessRegistry
from angstrompro.gui.widgets.curve_stack.prepare import prepare_entry, prepare_y_error


def _source_uds(data: np.ndarray | None = None) -> UdsDataStru:
    values = (
        np.arange(24, dtype=np.float64).reshape(3, 2, 4)
        if data is None
        else data
    )
    return UdsDataStru(
        name="didv",
        data=values,
        axes=[
            Axis(
                values=np.array([-1.0, 0.0, 1.0]),
                label="Bias",
                units="mV",
                axis_type=AxisType.BIAS,
            ),
            Axis(values=np.arange(2, dtype=float), label="Y", units="nm"),
            Axis(values=np.arange(4, dtype=float), label="X", units="nm"),
        ],
        info={"source": "measurement.3ds", "channel": "dI/dV"},
    )


def test_average_spectrum_core_defaults_to_spatial_standard_deviation() -> None:
    data = np.arange(24, dtype=np.float64).reshape(3, 2, 4)

    average, error = _average_spectrum_core(data)

    samples = data.reshape(3, -1)
    np.testing.assert_allclose(average, samples.mean(axis=1)[np.newaxis])
    np.testing.assert_allclose(
        error,
        samples.std(axis=1, ddof=1)[np.newaxis],
    )
    assert average.shape == error.shape == (1, 3)


def test_average_spectrum_can_return_standard_error() -> None:
    data = np.arange(24, dtype=np.float64).reshape(3, 2, 4)

    _average, deviation = _average_spectrum_core(data, STANDARD_DEVIATION)
    _average, standard_error = _average_spectrum_core(data, STANDARD_ERROR)

    np.testing.assert_allclose(
        standard_error,
        deviation / np.sqrt(data.shape[1] * data.shape[2]),
    )


def test_average_spectrum_single_spatial_sample_has_zero_error() -> None:
    average, error = _average_spectrum_core(
        np.array([[[2.0]], [[4.0]], [[8.0]]])
    )

    np.testing.assert_array_equal(average, [[2.0, 4.0, 8.0]])
    np.testing.assert_array_equal(error, np.zeros((1, 3)))


@pytest.mark.parametrize(
    "invalid, message",
    [
        (np.zeros((2, 3)), "requires data shaped"),
        (np.zeros((3, 0, 2)), "non-empty"),
        (np.ones((3, 2, 2), dtype=np.complex128), "real-valued"),
        (
            np.array([[[1.0]], [[np.nan]], [[3.0]]]),
            "finite data values",
        ),
    ],
)
def test_average_spectrum_core_rejects_unsupported_data(
    invalid: np.ndarray,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _average_spectrum_core(invalid)


def test_registered_average_spectrum_outputs_are_error_bar_compatible() -> None:
    source = _source_uds()
    entry = ProcessRegistry().get("spectral.average_spectrum_2d")

    result = ProcessRegistry().run(
        "spectral.average_spectrum_2d",
        {"data": source},
        {},
    )

    assert entry.label == "Average Spectrum 2D"
    assert [output.label for output in _OUT_AVERAGE_SPECTRUM] == [
        "Average Spectrum",
        "Average Spectrum Error",
    ]
    assert [item.name for item in result] == ["didv_avg", "didv_avg_std"]
    assert all(item.data.shape == (1, 3) for item in result)
    assert all(item.axes[-1].label == "Bias" for item in result)
    assert all(item.axes[-1].units == "mV" for item in result)
    assert all(item.axes[-1].axis_type is AxisType.BIAS for item in result)
    assert all(item.info["source"] == "measurement.3ds" for item in result)
    assert all(item.proc_history[-1].step == "spectral.average_spectrum_2d" for item in result)

    target_entry = prepare_entry(result[0].name, result[0])
    prepared_error = prepare_y_error(result[1], target_entry)
    np.testing.assert_allclose(prepared_error, result[1].data)


def test_registered_average_spectrum_standard_error_uses_sem_suffix() -> None:
    result = ProcessRegistry().run(
        "spectral.average_spectrum_2d",
        {"data": _source_uds()},
        {"error_quantity": STANDARD_ERROR},
    )

    assert result[1].name == "didv_avg_sem"
    assert result[1].proc_history[-1].params["error_quantity"] == STANDARD_ERROR


def test_average_spectrum_rejects_mismatched_energy_axis() -> None:
    source = _source_uds()
    source.axes[0].values = np.array([-1.0, 1.0])

    with pytest.raises(ValueError, match=r"axis\[0\].*energy dimension"):
        ProcessRegistry().run(
            "spectral.average_spectrum_2d",
            {"data": source},
            {},
        )
