from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from angstrompro.algorithms.line_circle_cut import (
    build_circle_cut_uds,
    build_line_cut_uds,
    build_point_spectra_uds,
)
from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.gui.modules.image_stack_viewer import (
    ImageStackViewer,
    _compute_curve_preview,
)
from angstrompro.gui.widgets.curve_stack.curve_stack_viewer_widget import (
    CurveStackViewerWidget,
)
from angstrompro.gui.widgets.image_stack_viewer_widget import (
    ImageStackViewerWidget,
)
from angstrompro.utils.qt_compat import QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _stack() -> UdsDataStru:
    data = np.arange(3 * 4 * 5, dtype=float).reshape(3, 4, 5)
    return UdsDataStru(
        name="source",
        data=data,
        axes=[
            Axis(
                values=np.asarray([-1.0, 0.0, 1.0]),
                label="Bias",
                units="V",
                axis_type=AxisType.BIAS,
            ),
            Axis(values=np.arange(4), label="Y", units="px"),
            Axis(values=np.arange(5), label="X", units="px"),
        ],
        info={"channel_display_name": "dI/dV"},
    )


def test_point_preview_builds_one_spectrum_per_picked_point() -> None:
    source = _stack()

    preview = build_point_spectra_uds(
        source, [(1, 2), (3, 4)], name="Live preview")

    assert preview.name == "Live preview"
    assert preview.data.shape == (2, 3)
    np.testing.assert_array_equal(preview.data[0], source.data[:, 1, 2])
    np.testing.assert_array_equal(preview.data[1], source.data[:, 3, 4])
    np.testing.assert_array_equal(preview.axes[-1].values, source.axes[0].values)
    assert preview.proc_history == []


def test_line_preview_orientation_changes_only_the_curve_stack_layout() -> None:
    source = _stack()

    distance_x = build_line_cut_uds(
        source,
        (1, 0),
        (1, 4),
        method="bresenham",
        orientation="layer_vs_distance",
        copy_process_history=False,
    )
    layer_x = build_line_cut_uds(
        source,
        (1, 0),
        (1, 4),
        method="bresenham",
        orientation="distance_vs_layer",
        copy_process_history=False,
    )

    np.testing.assert_array_equal(distance_x.data, source.data[:, 1, :])
    np.testing.assert_array_equal(layer_x.data, distance_x.data.T)
    assert distance_x.axes[-1].label == "Distance"
    assert layer_x.axes[-1].label == "Bias"
    assert distance_x.proc_history == []
    assert layer_x.proc_history == []


def test_circle_preview_uses_centre_edge_and_supports_both_orientations() -> None:
    source = _stack()

    angle_x = build_circle_cut_uds(
        source,
        (1, 2),
        (1, 3),
        orientation="layer_vs_theta",
        interpolation_order=0,
        num_points=8,
        copy_process_history=False,
    )
    layer_x = build_circle_cut_uds(
        source,
        (1, 2),
        (1, 3),
        orientation="theta_vs_layer",
        interpolation_order=0,
        num_points=8,
        copy_process_history=False,
    )

    assert angle_x.data.shape == (3, 8)
    np.testing.assert_array_equal(layer_x.data, angle_x.data.T)
    assert angle_x.axes[-1].label == "θ"
    assert layer_x.axes[-1].label == "Bias"
    assert angle_x.proc_history == []
    assert layer_x.proc_history == []


def test_circle_preview_worker_returns_temporary_curve_stack() -> None:
    preview, summary = _compute_curve_preview(
        _stack(),
        "circle",
        [(1.0, 2.0), (1.0, 3.0)],
        "layer_vs_theta",
        "interpolated",
        1,
        1,
        8,
    )

    assert preview.name == "Live preview"
    assert preview.data.shape == (3, 8)
    assert preview.proc_history == []
    assert summary == "Circle preview: 3 × 8"


def test_preview_samples_the_selected_display_representation() -> None:
    source = _stack()
    source.data = source.data + 1j * (source.data + 100.0)
    displayed = np.abs(source.data)

    preview, _summary = _compute_curve_preview(
        source,
        "circle",
        [(1.0, 2.0), (1.0, 3.0)],
        "layer_vs_theta",
        "interpolated",
        1,
        1,
        8,
        display_data=displayed,
    )
    expected = build_circle_cut_uds(
        UdsDataStru(
            name=source.name,
            data=displayed,
            axes=source.axes,
            info=source.info,
        ),
        (1.0, 2.0),
        (1.0, 3.0),
        num_points=8,
        copy_process_history=False,
    )

    np.testing.assert_allclose(preview.data, expected.data)


def test_primary_type_change_exposes_imaginary_stack_and_emits(qapp) -> None:
    source = _stack()
    source.data = source.data + 1j * (source.data + 10.0)
    panel = ImageStackViewerWidget()
    panel.setUdsData(source)
    messages = []
    panel.sendMsgSignal.connect(
        lambda idx: messages.append(panel.msg_type[idx]))

    panel.ui_cb_image_data_type.setCurrentText("Imag")

    np.testing.assert_array_equal(
        panel.currentDataRepresentation(), np.imag(source.data))
    assert "IMAGE_DATA_TYPE_CHANGED" in messages
    panel.close()


def test_curve_preview_template_loads_only_when_preference_changes() -> None:
    viewer = Mock()
    module = SimpleNamespace(
        _curve_preview_template_name=None,
        _curve_preview_viewer=viewer,
    )
    configured = {"curve_preview": {"default_template": "publication"}}

    ImageStackViewer._apply_curve_preview_template(module, configured)
    ImageStackViewer._apply_curve_preview_template(module, configured)

    viewer.apply_preload_template.assert_called_once_with("publication")
    viewer.reset_template_style.assert_not_called()

    ImageStackViewer._apply_curve_preview_template(
        module, {"curve_preview": {"default_template": ""}})

    viewer.reset_template_style.assert_called_once_with()


def test_replacing_live_preview_keeps_visibility_state(qapp) -> None:
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    first = build_point_spectra_uds(
        _stack(), [(1, 2), (3, 4)], name="Live preview")
    second = build_point_spectra_uds(
        _stack(), [(2, 3)], name="Live preview")

    viewer.add_dataset("Live preview", first)
    viewer.add_dataset("Live preview", second)

    assert "Live preview" in viewer._checked
    assert viewer._checked["Live preview"] == [True]
    assert viewer._plot_widget._checked is viewer._checked
    assert list(viewer._plot_widget._lines) == [("Live preview", 0)]
    viewer.close()
