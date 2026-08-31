from __future__ import annotations

import numpy as np
import pytest

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.modules.planewave_synthesiser import (
    PlanewaveSynthesiser,
    WaveVectorSettings,
    _make_planewave_uds,
    _recipe_to_wave_settings,
    _wave_settings_to_recipe,
)
from angstrompro.io.uds_io import load, save


def _sample_waves() -> tuple[WaveVectorSettings, ...]:
    return (
        WaveVectorSettings(
            qx=2.5,
            qy=-3.25,
            amplitude_min=-0.5,
            amplitude_max=2.5,
            amplitude_slider=37,
            phase_min=-6.28,
            phase_max=6.28,
            phase_slider=82,
        ),
        WaveVectorSettings(
            qx=-0.125,
            qy=8.75,
            amplitude_min=0.25,
            amplitude_max=0.75,
            amplitude_slider=61,
            phase_min=-1.0,
            phase_max=2.0,
            phase_slider=19,
        ),
    )


def test_planewave_recipe_round_trip_preserves_all_controls() -> None:
    waves = _sample_waves()

    image_size, restored = _recipe_to_wave_settings(
        _wave_settings_to_recipe(192, waves)
    )

    assert image_size == 192
    assert restored == waves


def test_planewave_recipe_survives_uds_hdf5_round_trip(tmp_path) -> None:
    waves = _sample_waves()
    uds = _make_planewave_uds(
        np.zeros((32, 32), dtype=np.float64),
        32,
        waves,
        name="planewave_snapshot",
    )

    assert set(uds.info) == {"_source_format", "planewave"}
    assert uds.info["_source_format"] == "planewave_synthesiser"

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
