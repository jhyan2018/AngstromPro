from __future__ import annotations

import numpy as np

from angstrompro.algorithms.isocontour import isoline_2d
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.io.uds_io import load, save


def _high_dimensional_uds() -> UdsDataStru:
    shape = (2, 5, 3, 6)
    axis_values = [
        np.arange(shape[0], dtype=float),
        np.linspace(-1.0, 1.0, shape[1]),
        np.arange(shape[2], dtype=float),
        np.linspace(-2.0, 2.0, shape[3]),
    ]
    data = np.empty(shape, dtype=np.float64)
    for selector_0 in range(shape[0]):
        for selector_2 in range(shape[2]):
            data[selector_0, :, selector_2, :] = (
                axis_values[1][:, None] + axis_values[3][None, :]
                + 0.1 * selector_0 + 0.05 * selector_2
            )
    return UdsDataStru(
        name="higher dimensional map",
        data=data,
        axes=[
            Axis(values, label=f"axis {index}")
            for index, values in enumerate(axis_values)
        ],
    )


def test_isoline_iterates_every_non_plane_axis_and_records_coordinates() -> None:
    progress = []

    result = isoline_2d(
        {"data": _high_dimensional_uds()},
        {
            "levels": "0.0",
            "method": "marching_squares",
            "plane_axes": "3,1",
            "interpolate": False,
            "interp_factor": 4,
        },
        progress_callback=lambda current, total: progress.append((current, total)),
    )

    assert result.data.shape == (2, 5, 3, 6)
    assert len(result.isocontours) == 6
    assert progress[-1] == (6, 6)
    assert result.isocontours[0].source_axes == (1, 3)
    assert result.isocontours[0].coordinate_axes == (3, 1)
    assert result.isocontours[0].selector_indices == ((0, 0), (2, 0))
    assert result.isocontours[-1].selector_indices == ((0, 1), (2, 2))


def test_isoline_selector_metadata_survives_uds_round_trip(tmp_path) -> None:
    result = isoline_2d(
        {"data": _high_dimensional_uds()},
        {
            "levels": "0.0",
            "method": "marching_squares",
            "plane_axes": "1,3",
            "interpolate": False,
            "interp_factor": 4,
        },
    )
    path = tmp_path / "contours.uds"

    save(path, result)
    restored = load(path)

    assert len(restored.isocontours) == 6
    first = restored.isocontours[0]
    assert first.source_axes == (1, 3)
    assert first.coordinate_axes == (3, 1)
    assert first.selector_indices == ((0, 0), (2, 0))


def test_legacy_isoline_without_selector_metadata_remains_readable(tmp_path) -> None:
    import h5py

    result = isoline_2d(
        {"data": _high_dimensional_uds()},
        {
            "levels": "0.0",
            "method": "marching_squares",
            "plane_axes": "1,3",
            "interpolate": False,
            "interp_factor": 4,
        },
    )
    path = tmp_path / "legacy-contours.uds"
    save(path, result)
    with h5py.File(path, "r+") as handle:
        contour_group = handle["isocontours/0"]
        del contour_group.attrs["coordinate_axes"]
        del contour_group.attrs["selector_indices"]

    restored = load(path)

    assert restored.isocontours[0].source_axes == (1, 3)
    assert restored.isocontours[0].coordinate_axes == ()
    assert restored.isocontours[0].selector_indices == ()
