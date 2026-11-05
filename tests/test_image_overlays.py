from __future__ import annotations

import numpy as np

from angstrompro.core.data.image_overlay_data import (
    CircleOverlay,
    EllipseOverlay,
    PointOverlay,
    PolylineOverlay,
)
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.gui.widgets.image_stack_viewer_widget import ImageStackViewerWidget
from angstrompro.io.uds_io import _dict_to_uds, _uds_to_dict, load, save
from angstrompro.utils.qt_compat import QtWidgets


def _uds_with_overlays() -> UdsDataStru:
    return UdsDataStru(
        name="image",
        data=np.zeros((2, 32, 32), dtype=float),
        image_overlays=[
            CircleOverlay(
                name="ring",
                layer_index=1,
                layer_value=0.2,
                source_axes=(1, 2),
                center=(16.0, 15.5),
                radius=7.25,
                method="gaussian",
                style={"color": "#00ffff", "width": 2.0},
                metadata={"q_over_G": np.float64(0.35)},
            ),
            EllipseOverlay(
                center=(10.0, 12.0),
                radius_row=3.0,
                radius_column=5.0,
                rotation_degrees=25.0,
            ),
            PolylineOverlay(
                vertices=np.asarray([[1.0, 2.0], [3.0, 4.0]]),
                closed=True,
            ),
            PointOverlay(points=np.asarray([[8.0, 9.0], [10.0, 11.0]])),
        ],
    )


def test_typed_image_overlays_survive_uds_round_trip(tmp_path) -> None:
    path = tmp_path / "overlays.uds"
    save(path, _uds_with_overlays())

    restored = load(path)

    assert [type(value) for value in restored.image_overlays] == [
        CircleOverlay,
        EllipseOverlay,
        PolylineOverlay,
        PointOverlay,
    ]
    circle = restored.image_overlays[0]
    assert circle.name == "ring"
    assert circle.layer_index == 1
    assert circle.layer_value == 0.2
    assert circle.source_axes == (1, 2)
    assert circle.center == (16.0, 15.5)
    assert circle.radius == 7.25
    assert circle.style == {"color": "#00ffff", "width": 2.0}
    assert circle.metadata == {"q_over_G": 0.35}
    np.testing.assert_array_equal(
        restored.image_overlays[2].vertices,
        [[1.0, 2.0], [3.0, 4.0]],
    )
    np.testing.assert_array_equal(
        restored.image_overlays[3].points,
        [[8.0, 9.0], [10.0, 11.0]],
    )


def test_image_overlays_appear_in_uds_inspector() -> None:
    overlay_node = next(
        node for node in _uds_with_overlays().inspect_fields()
        if node["label"] == "image_overlays"
    )

    assert overlay_node["summary"] == "4 feature(s)"
    assert overlay_node["children"][0]["label"] == "ring"
    assert any(
        child["label"] == "radius" and child["value"] == "7.25"
        for child in overlay_node["children"][0]["children"]
    )


def test_image_overlays_survive_json_native_embedded_uds_conversion() -> None:
    restored = _dict_to_uds(_uds_to_dict(_uds_with_overlays()))

    assert isinstance(restored.image_overlays[0], CircleOverlay)
    assert restored.image_overlays[0].radius == 7.25
    np.testing.assert_array_equal(
        restored.image_overlays[2].vertices,
        [[1.0, 2.0], [3.0, 4.0]],
    )


def test_image_stack_viewer_draws_only_the_current_layers_overlays() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = UdsDataStru.from_array(np.zeros((2, 32, 32)), "image")
    source.image_overlays = [
        CircleOverlay(name="first", layer_index=0, center=(16, 16), radius=5),
        CircleOverlay(
            name="hidden", layer_index=0, center=(16, 16), radius=6,
            style={"visible": False},
        ),
        CircleOverlay(name="second", layer_index=1, center=(16, 16), radius=7),
    ]
    widget = ImageStackViewerWidget()
    try:
        assert app is not None
        widget.setUdsData(source)
        assert len(widget._iso_items) == 1
        assert widget._iso_items[0].toolTip() == "first"

        widget.ui_sb_image_layers.setValue(1)
        app.processEvents()
        assert len(widget._iso_items) == 1
        assert widget._iso_items[0].toolTip() == "second"
    finally:
        widget.close()
