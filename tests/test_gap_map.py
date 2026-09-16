from __future__ import annotations

import numpy as np
import pytest

from angstrompro.algorithms.gap_map import (
    _OUT_GAP,
    _energy_value_range_to_indices,
    _gap_map_core,
)
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes.registry import ProcessRegistry


def _spectra() -> tuple[np.ndarray, np.ndarray, float]:
    energies = np.linspace(1.40e-3, 1.65e-3, 31)
    peak_energy = 1.55e-3
    perfect = 2.0e-12 - 0.8e-12 * ((energies - peak_energy) / 1.0e-4) ** 2

    rng = np.random.default_rng(20260916)
    noisy = perfect + rng.normal(scale=0.08e-12, size=energies.size)

    data = np.empty((energies.size, 2, 2), dtype=np.float64)
    data[:, 0, 0] = perfect
    data[:, 0, 1] = noisy
    data[:, 1, 0] = 0.0
    data[:, 1, 1] = 3.0e-12
    return data, energies, peak_energy


def _source_uds() -> UdsDataStru:
    data, energies, _ = _spectra()
    return UdsDataStru(
        name="didv",
        data=data,
        axes=[
            Axis(values=energies, label="Bias", units="V"),
            Axis(values=np.arange(2, dtype=np.float64), label="Y", units="px"),
            Axis(values=np.arange(2, dtype=np.float64), label="X", units="px"),
        ],
        info={"source": "measurement.3ds"},
    )


def test_gap_map_fit_is_stable_for_picoamp_scale_and_reports_real_r_squared() -> None:
    data, energies, peak_energy = _spectra()

    gap, fit_quality = _gap_map_core(data, energies, 2, None, None)

    assert gap.shape == (1, 2, 2)
    assert fit_quality.shape == (1, 2, 2)
    assert gap[0, 0, 0] == pytest.approx(peak_energy, abs=1e-12)
    assert fit_quality[0, 0, 0] == pytest.approx(1.0, abs=1e-12)
    assert 0.0 < fit_quality[0, 0, 1] < 1.0

    # A peak and R² are undefined for empty or constant spectra. Returning
    # zero makes zero-padded/incomplete pixels visibly invalid.
    assert gap[0, 1, 0] == 0.0
    assert fit_quality[0, 1, 0] == 0.0
    assert gap[0, 1, 1] == 0.0
    assert fit_quality[0, 1, 1] == 0.0


def test_gap_map_rejects_too_few_energy_points_for_polynomial_order() -> None:
    data, energies, _ = _spectra()

    with pytest.raises(ValueError, match="requires at least 5 energy points"):
        _gap_map_core(data, energies, 4, energies[0], energies[3])


def test_physical_energy_range_maps_to_nearest_layers_in_either_axis_order() -> None:
    ascending = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    descending = ascending[::-1]

    assert _energy_value_range_to_indices(ascending, -0.8, 1.2) == (1, 3)
    assert _energy_value_range_to_indices(descending, -0.8, 1.2) == (1, 3)
    assert _energy_value_range_to_indices(ascending, 1.2, -0.8) == (1, 3)
    assert _energy_value_range_to_indices(descending, None, None) == (0, 4)


def test_gap_map_schema_and_all_outputs_receive_source_and_history() -> None:
    assert _OUT_GAP[1].label == "R² Fit Quality Map"
    assert "coefficient-of-determination" in _OUT_GAP[1].description.lower()

    result = ProcessRegistry().run(
        "spectral.gap_map_2d",
        {"data": _source_uds()},
        {"order": 2},
    )

    assert isinstance(result, list)
    assert [item.name for item in result] == ["didv_gm", "didv_R2"]
    assert result[0].axes[0].units == "V"
    for item in result:
        assert item.info["source"] == "measurement.3ds"
        assert item.proc_history[-1].step == "spectral.gap_map_2d"
        assert item.proc_history[-1].input_item_names == ["didv"]
