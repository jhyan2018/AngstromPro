from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest

from angstrompro.io.formats.nanonis_sxm import load


def _write_sxm(
    path: Path,
    *,
    channels: list[tuple[str, str]],
    rasters: list[np.ndarray],
) -> None:
    data_rows = [
        "Channel\tName\tUnit\tDirection\tCalibration\tOffset",
        *(
            f"{index}\t{name}\tA\t{direction}\t1\t0"
            for index, (name, direction) in enumerate(channels)
        ),
    ]
    header = (
        ":SCAN_PIXELS:\r\n"
        "2 2\r\n"
        ":SCAN_RANGE:\r\n"
        "2e-9 2e-9\r\n"
        ":DATA_INFO:\r\n"
        + "\r\n".join(data_rows)
        + "\r\n"
        ":BIAS:\r\n"
        "0.1\r\n"
        ":SCANIT_END:\r\n"
        "\r\n"
        "\r\n"
    ).encode("latin-1")
    payload = np.asarray(rasters, dtype=">f4").tobytes()
    path.write_bytes(header + b"\x1a\x04" + payload)


def test_forward_only_channel_is_loaded_as_stored(tmp_path: Path) -> None:
    path = tmp_path / "forward.sxm"
    _write_sxm(
        path,
        channels=[("Signal", "forward")],
        rasters=[np.array([[1.0, 2.0], [3.0, 4.0]])],
    )

    result = load(path, channel_indices=[0])

    np.testing.assert_array_equal(
        result.data[0], np.array([[3.0, 4.0], [1.0, 2.0]]))
    assert result.info["channel_direction_declared"] == "forward"
    assert result.info["channel_direction_loaded"] == "forward"
    assert result.info["direction_inferred"] is False


def test_backward_only_channel_is_reoriented_along_x(tmp_path: Path) -> None:
    path = tmp_path / "backward.sxm"
    _write_sxm(
        path,
        channels=[("Signal", "backward")],
        rasters=[np.array([[1.0, 2.0], [3.0, 4.0]])],
    )

    result = load(path, channel_indices=[0])

    np.testing.assert_array_equal(
        result.data[0], np.array([[4.0, 3.0], [2.0, 1.0]]))
    assert result.info["channel_direction_declared"] == "backward"
    assert result.info["channel_direction_loaded"] == "backward"
    assert result.info["direction_inferred"] is False


def test_both_channel_uses_forward_raster(tmp_path: Path) -> None:
    path = tmp_path / "both.sxm"
    _write_sxm(
        path,
        channels=[("Signal", "both")],
        rasters=[
            np.array([[1.0, 2.0], [3.0, 4.0]]),
            np.array([[20.0, 10.0], [40.0, 30.0]]),
        ],
    )

    result = load(path, channel_indices=[0])

    np.testing.assert_array_equal(
        result.data[0], np.array([[3.0, 4.0], [1.0, 2.0]]))
    assert result.info["channel_direction_declared"] == "both"
    assert result.info["channel_direction_loaded"] == "forward"
    assert result.info["direction_inferred"] is False


def test_all_both_with_one_raster_per_channel_loads_as_single(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / "exported_slice.sxm"
    _write_sxm(
        path,
        channels=[("Signal", "both")],
        rasters=[np.array([[1.0, 2.0], [3.0, 4.0]])],
    )

    with caplog.at_level(logging.WARNING):
        result = load(path, channel_indices=[0])

    np.testing.assert_array_equal(
        result.data[0], np.array([[3.0, 4.0], [1.0, 2.0]]))
    assert result.info["channel_direction_declared"] == "both"
    assert result.info["channel_direction_loaded"] == "single"
    assert result.info["direction_inferred"] is True
    assert "one raster per channel" in result.info["direction_warning"]
    assert "one raster per channel" in caplog.text


def test_ambiguous_layer_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.sxm"
    _write_sxm(
        path,
        channels=[("Signal", "both")],
        rasters=[
            np.zeros((2, 2)),
            np.ones((2, 2)),
            np.full((2, 2), 2.0),
        ],
    )

    with pytest.raises(ValueError, match="cannot be inferred safely"):
        load(path, channel_indices=[0])


def test_unknown_direction_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unknown.sxm"
    _write_sxm(
        path,
        channels=[("Signal", "sideways")],
        rasters=[np.zeros((2, 2))],
    )

    with pytest.raises(ValueError, match="Unsupported DATA_INFO direction"):
        load(path, channel_indices=[0])
