from __future__ import annotations

import numpy as np
import pytest

from angstrompro.algorithms.fft import _make_1d_window, fft1d
from angstrompro.core.data.uds_data import (
    Axis,
    AxisType,
    FFT_DOMAIN_KEY,
    FFT_TRANSFORM_KEY,
    FFT_WINDOW_KEY,
    UdsDataStru,
    is_fft_uds,
)
from angstrompro.core.processes import ProcessRegistry


def _curve_stack() -> UdsDataStru:
    sample_count = 16
    time = np.arange(sample_count, dtype=float) * 0.25
    data = np.vstack((
        np.sin(2.0 * np.pi * 0.5 * time),
        np.cos(2.0 * np.pi * 1.0 * time),
    ))
    return UdsDataStru(
        name="signals",
        data=data,
        axes=[
            Axis(
                values=np.array([0.0, 1.0]),
                label="Curve",
                axis_type=AxisType.INDEX,
            ),
            Axis(
                values=time,
                label="Time",
                units="s",
                axis_type=AxisType.TIME,
            ),
        ],
        info={"column_name": "Signal (V)"},
    )


def _params(window="none", normalized=True):
    return {
        "window": window,
        "tukey_alpha": 0.4,
        "normalized": normalized,
    }


def test_fft_1d_is_registered_for_curve_stacks() -> None:
    entry = ProcessRegistry().get("spectral.fft_1d")

    assert entry.label == "FFT 1D"
    assert entry.schema.inputs[0].ndim == 2
    assert entry.schema.outputs[0].ndim == 2
    assert entry.schema.defaults()["window"] == "none"


def test_fft_1d_transforms_every_curve_and_builds_frequency_axis() -> None:
    source = _curve_stack()

    result = fft1d({"data": source}, _params())

    expected = np.fft.fftshift(
        np.fft.fft(source.data, axis=-1), axes=-1
    ) / source.data.shape[-1]
    np.testing.assert_allclose(result.data, expected)
    np.testing.assert_allclose(
        result.axes[1].values,
        np.fft.fftshift(np.fft.fftfreq(16, d=0.25)),
    )
    assert result.axes[1].label == "f_Time"
    assert result.axes[1].units == "Hz"
    assert result.axes[1].axis_type is AxisType.FREQUENCY
    assert result.axes[0] is not source.axes[0]
    assert result.name == "signals_fft"
    assert result.info[FFT_DOMAIN_KEY] == "frequency"
    assert result.info[FFT_TRANSFORM_KEY] == "fft_1d"
    assert result.info[FFT_WINDOW_KEY] == "none"
    assert is_fft_uds(result)


@pytest.mark.parametrize(
    "window",
    ["none", "hann", "hamming", "tukey", "blackman", "blackman-harris"],
)
def test_fft_1d_supports_each_window(window) -> None:
    source = _curve_stack()

    result = fft1d({"data": source}, _params(window, normalized=False))

    taper = _make_1d_window(window, source.data.shape[-1], 0.4)
    expected = np.fft.fftshift(
        np.fft.fft(source.data * taper[np.newaxis, :], axis=-1), axes=-1
    )
    np.testing.assert_allclose(result.data, expected)
    assert result.info[FFT_WINDOW_KEY] == window


def test_fft_1d_rejects_nonuniform_sample_axis() -> None:
    source = _curve_stack()
    source.axes[1].values[5] += 0.05

    with pytest.raises(ValueError, match="uniformly sampled"):
        fft1d({"data": source}, _params())
