from __future__ import annotations

import numpy as np
import pytest

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.modules.planewave_synthesiser import (
    PlanewaveSynthesiser,
    WaveVectorSettings,
    WaveVectorRow,
    _make_planewave_uds,
    _normalise_phase,
    _recipe_to_wave_settings,
    _wave_settings_to_recipe,
)
from angstrompro.io.uds_io import load, save
from angstrompro.utils.qt_compat import QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sample_waves() -> tuple[WaveVectorSettings, ...]:
    return (
        WaveVectorSettings(
            qx=2.5,
            qy=-3.25,
            amplitude=2.125,
            phase=0.75,
        ),
        WaveVectorSettings(
            qx=-0.125,
            qy=8.75,
            amplitude=-0.75,
            phase=-1.25,
        ),
    )


def test_planewave_recipe_round_trip_preserves_all_controls() -> None:
    waves = _sample_waves()

    image_size, restored = _recipe_to_wave_settings(
        _wave_settings_to_recipe(192, waves)
    )

    assert image_size == 192
    assert restored == waves


def test_planewave_recipe_stores_direct_values() -> None:
    recipe = _wave_settings_to_recipe(192, _sample_waves())

    assert recipe["schema_version"] == 2
    assert recipe["waves"][0] == {
        "qx": 2.5,
        "qy": -3.25,
        "amplitude": 2.125,
        "phase": 0.75,
    }


def test_legacy_slider_recipe_converts_to_direct_values() -> None:
    recipe = {
        "schema_version": 1,
        "image_size": 128,
        "waves": [{
            "qx": 2.5,
            "qy": -3.25,
            "amplitude_min": -0.5,
            "amplitude_max": 2.5,
            "amplitude_slider": 37,
            "phase_min": -6.28,
            "phase_max": 6.28,
            "phase_slider": 82,
        }],
    }

    image_size, waves = _recipe_to_wave_settings(recipe)

    assert image_size == 128
    assert waves[0].qx == 2.5
    assert waves[0].qy == -3.25
    assert waves[0].amplitude == pytest.approx(0.61)
    assert waves[0].phase == pytest.approx(_normalise_phase(4.0192))
    snapshot = UdsDataStru(
        name="legacy_planewave_snapshot",
        data=np.zeros((1, 128, 128), dtype=np.float64),
        info={"source": "planewave_synthesiser", "planewave": recipe},
    )
    assert PlanewaveSynthesiser._recipe_from_workspace_item(
        WorkspaceItem(payload=snapshot)
    ) == recipe


def test_wave_row_accepts_direct_amplitude_and_phase(qapp) -> None:
    row = WaveVectorRow(0)
    changed = []
    row.paramsChanged.connect(changed.append)

    row._sb_amplitude.setValue(-2.5)
    row._sb_phase.setValue(1.234567)

    assert row.amplitude == pytest.approx(-2.5)
    assert row.phase == pytest.approx(1.234567)
    assert row.wave_settings() == WaveVectorSettings(
        amplitude=-2.5,
        phase=1.234567,
    )
    assert changed == [0, 0]
    assert row._sb_phase.minimum() == pytest.approx(-np.pi)
    assert row._sb_phase.maximum() == pytest.approx(np.pi)
    assert row._lb_phase_conversion.text() == "= 70.735°"
    assert row._le_qx.width() >= 82
    assert row._le_qy.width() >= 82
    assert row._sb_amplitude.minimumWidth() >= 140
    assert row._cb_phase_unit.width() >= 88
    assert row._sb_phase.minimumWidth() >= 140
    assert row._lb_phase_conversion.minimumWidth() >= 112

    row._cb_phase_unit.setCurrentText("deg")

    assert row._sb_phase.minimum() == pytest.approx(-180.0)
    assert row._sb_phase.maximum() == pytest.approx(180.0)
    assert row._sb_phase.value() == pytest.approx(np.rad2deg(1.234567))
    assert row._lb_phase_conversion.text() == "= 1.234567 rad"
    assert changed == [0, 0]

    row._sb_phase.setValue(-45.0)

    assert row.phase == pytest.approx(-np.pi / 4.0)
    assert row._lb_phase_conversion.text() == "= -0.785398 rad"
    assert changed == [0, 0, 0]
    row.close()


def test_planewave_recipe_survives_uds_hdf5_round_trip(tmp_path) -> None:
    waves = _sample_waves()
    uds = _make_planewave_uds(
        np.zeros((32, 32), dtype=np.float64),
        32,
        waves,
        name="planewave_snapshot",
    )

    assert set(uds.info) == {"source", "planewave"}
    assert uds.info["source"] == "planewave_synthesiser"

    path = tmp_path / "planewave_snapshot.uds"
    save(path, uds)
    loaded = load(path)

    assert _recipe_to_wave_settings(loaded.info["planewave"]) == (32, waves)
    item = WorkspaceItem(payload=loaded)
    assert (
        PlanewaveSynthesiser._recipe_from_workspace_item(item)
        == loaded.info["planewave"]
    )


def test_old_planewave_snapshot_has_no_restore_recipe() -> None:
    legacy = UdsDataStru(
        name="old_planewave_snapshot",
        data=np.zeros((1, 16, 16), dtype=np.float64),
        info={"_source_format": "planewave_synthesiser"},
    )

    assert "_source_format" not in legacy.info
    assert "source" not in legacy.info
    assert PlanewaveSynthesiser._recipe_from_workspace_item(
        WorkspaceItem(payload=legacy)
    ) is None


def test_planewave_recipe_rejects_unsupported_schema_version() -> None:
    recipe = _wave_settings_to_recipe(256, _sample_waves())
    recipe["schema_version"] = 999

    with pytest.raises(ValueError, match="unsupported schema"):
        _recipe_to_wave_settings(recipe)


@pytest.mark.parametrize("key,value", [
    ("image_size", 15),
    ("image_size", 4097),
])
def test_planewave_recipe_rejects_invalid_image_size(key, value) -> None:
    recipe = _wave_settings_to_recipe(256, _sample_waves())
    recipe[key] = value

    with pytest.raises(ValueError, match="image_size"):
        _recipe_to_wave_settings(recipe)
