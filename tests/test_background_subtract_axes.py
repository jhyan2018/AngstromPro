"""Per-line subtraction follows the selected image axis in both callers."""

from __future__ import annotations

import numpy as np
import pytest

from angstrompro.algorithms.background_subtract import (
    _SCHEMA, _bg_subtract_per_line, bg_subtract,
)
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.gui.modules.data_browser.thumbnail_renderers import render_uds_3d


@pytest.fixture
def vertical_lines() -> np.ndarray:
    """Each column has a different first-order Y background."""
    y = np.arange(5, dtype=float)[:, None]
    slope = np.array([1.0, 2.0, 3.0, 4.0])[None, :]
    offset = np.array([0.0, 5.0, -2.0, 8.0])[None, :]
    return y * slope + offset


@pytest.fixture
def horizontal_lines() -> np.ndarray:
    """Each row has a different first-order X background."""
    x = np.arange(4, dtype=float)[None, :]
    slope = np.array([1.0, 2.0, 3.0, 4.0, 5.0])[:, None]
    offset = np.array([0.0, 5.0, -2.0, 8.0, -4.0])[:, None]
    return x * slope + offset


def test_column_default_and_row_option(vertical_lines, horizontal_lines):
    column_result = _bg_subtract_per_line(vertical_lines, 1)
    row_result = _bg_subtract_per_line(horizontal_lines, 1, line_axis="X")

    np.testing.assert_allclose(column_result, np.mean(vertical_lines), atol=1e-12)
    np.testing.assert_allclose(row_result, np.mean(horizontal_lines), atol=1e-12)
    assert not np.allclose(
        _bg_subtract_per_line(vertical_lines, 1, line_axis="X"),
        np.mean(vertical_lines))
    assert not np.allclose(
        _bg_subtract_per_line(horizontal_lines, 1, line_axis="Y"),
        np.mean(horizontal_lines))


def test_registered_process_exposes_and_uses_line_axis(vertical_lines,
                                                     horizontal_lines):
    assert _SCHEMA.defaults()["line_axis"] == "Y"
    src = UdsDataStru.from_array(vertical_lines[None, :, :], "vertical")
    result = bg_subtract({"data": src}, {"method": "PerLine", "order": 1,
                                         "line_axis": "Y"})
    np.testing.assert_allclose(result.data[0], np.mean(vertical_lines), atol=1e-12)
    np.testing.assert_array_equal(src.data[0], vertical_lines)

    src = UdsDataStru.from_array(horizontal_lines[None, :, :], "horizontal")
    result = bg_subtract({"data": src}, {"method": "PerLine", "order": 1,
                                         "line_axis": "X"})
    np.testing.assert_allclose(result.data[0], np.mean(horizontal_lines), atol=1e-12)


@pytest.mark.parametrize("method,axis", [
    ("Per scan line", "Y"),
    ("Per image row (X)", "X"),
])
def test_data_browser_direction_and_display_only(vertical_lines,
                                                horizontal_lines, method, axis):
    image = vertical_lines if axis == "Y" else horizontal_lines
    src = UdsDataStru.from_array(image[None, :, :], "Z")
    fig = render_uds_3d(src, options={"channel_id": "Z",
                                      "z_background_method": method})
    try:
        display = np.asarray(fig.axes[0].images[0].get_array())
        np.testing.assert_allclose(display, np.mean(image), atol=1e-12)
        np.testing.assert_array_equal(src.data[0], image)
    finally:
        fig.clear()


def test_browser_leaves_other_channels_unmodified(vertical_lines):
    src = UdsDataStru.from_array(vertical_lines[None, :, :], "Current")
    fig = render_uds_3d(src, options={"channel_id": "Current",
                                      "z_background_method": "Per scan line"})
    try:
        np.testing.assert_array_equal(fig.axes[0].images[0].get_array(),
                                      vertical_lines)
    finally:
        fig.clear()
