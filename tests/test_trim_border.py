"""One-pixel border trimming for iterative image-quality workflows."""

import numpy as np
import pytest

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import ProcessRegistry


def _image(shape=(2, 8, 10)):
    data = np.arange(np.prod(shape)).reshape(shape)
    return UdsDataStru(
        name="image",
        data=data,
        axes=[
            Axis(np.arange(shape[0]), "Layer", ""),
            Axis(np.arange(shape[1]) * 2.0, "Row", "nm"),
            Axis(np.arange(shape[2]) * 3.0, "Column", "nm"),
        ],
    )


def test_trim_border_removes_one_pixel_per_edge_and_preserves_axes():
    source = _image()
    entry = ProcessRegistry().get("spatial.trim_border_2d")
    assert entry.label == "Trim One-Pixel Border 2D"
    assert entry.category == ProcessRegistry().get("spatial.crop_square_2d").category
    first = ProcessRegistry().run(entry.name, {"data": source}, {})
    second = ProcessRegistry().run(entry.name, {"data": first}, {})

    np.testing.assert_array_equal(first.data, source.data[:, 1:-1, 1:-1])
    np.testing.assert_array_equal(second.data, source.data[:, 2:-2, 2:-2])
    np.testing.assert_array_equal(first.axes[0].values, source.axes[0].values)
    np.testing.assert_array_equal(first.axes[1].values, source.axes[1].values[1:-1])
    np.testing.assert_array_equal(first.axes[2].values, source.axes[2].values[1:-1])
    assert first.axes[1].units == first.axes[2].units == "nm"
    assert not np.shares_memory(first.data, source.data)
    np.testing.assert_array_equal(source.data, _image().data)


def test_trim_border_rejects_image_too_small_for_another_square_crop():
    with pytest.raises(ValueError, match="at least 4 x 4"):
        ProcessRegistry().run(
            "spatial.trim_border_2d", {"data": _image((1, 2, 6))}, {}
        )
