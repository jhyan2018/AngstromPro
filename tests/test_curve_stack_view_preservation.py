from __future__ import annotations

import numpy as np
import pytest

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.gui.widgets.curve_stack.curve_stack_viewer_widget import (
    CurveStackViewerWidget,
)
from angstrompro.gui.widgets.curve_stack.runtime_scene import RuntimeScene
from angstrompro.utils.qt_compat import QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _curves(name: str = "curves") -> UdsDataStru:
    x = np.linspace(-2.0, 2.0, 9)
    data = np.vstack((x**2, x**2 + 4.0, x**2 + 8.0))
    return UdsDataStru(
        name=name,
        data=data,
        axes=[
            Axis(
                values=np.array([10.0, 20.0, 30.0]),
                label="Layer",
                axis_type=AxisType.INDEX,
            ),
            Axis(
                values=x,
                label="Bias",
                units="V",
                axis_type=AxisType.BIAS,
            ),
        ],
        info={"column_name": "Current (A)"},
    )


def _viewer() -> CurveStackViewerWidget:
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    viewer.set_runtime_scene(RuntimeScene())
    viewer.add_dataset("curves", _curves())
    return viewer


def _assert_limits(ax, xlim, ylim) -> None:
    np.testing.assert_allclose(ax.get_xlim(), xlim)
    np.testing.assert_allclose(ax.get_ylim(), ylim)


def test_stack_visibility_and_style_rebuilds_keep_live_view(qapp) -> None:
    viewer = _viewer()
    widget = viewer._plot_widget
    ax = widget._ax
    ax.set_xlim(-0.75, 0.5)
    ax.set_ylim(1.5, 7.5)
    expected_x = ax.get_xlim()
    expected_y = ax.get_ylim()

    widget.set_line_visible("curves", 1, False)
    _assert_limits(ax, expected_x, expected_y)

    viewer._check_all(False)
    _assert_limits(widget._ax, expected_x, expected_y)

    widget.set_offset(1.25)
    _assert_limits(widget._ax, expected_x, expected_y)

    viewer.set_rcparams_delta({"font.size": 14.0})
    _assert_limits(widget._ax, expected_x, expected_y)
    viewer.close()


def test_colormap_visibility_masks_fixed_rows_and_keeps_color_scale(qapp) -> None:
    viewer = _viewer()
    viewer._set_mode("colormap")
    widget = viewer._plot_widget
    ax = widget._ax
    ax.set_xlim(-0.8, 0.8)
    ax.set_ylim(12.0, 28.0)
    expected_x = ax.get_xlim()
    expected_y = ax.get_ylim()
    expected_clim = widget._colorbar.mappable.get_clim()

    widget.set_line_visible("curves", 1, False)

    _assert_limits(widget._ax, expected_x, expected_y)
    assert widget._colorbar.mappable.get_clim() == pytest.approx(expected_clim)
    mask = np.ma.getmaskarray(widget._colorbar.mappable.get_array())
    assert int(mask.sum()) == _curves().data.shape[-1]

    viewer._check_all(False)
    _assert_limits(widget._ax, expected_x, expected_y)
    assert widget._colorbar.mappable.get_clim() == pytest.approx(expected_clim)

    widget._cmap_combo.setCurrentText("viridis")
    _assert_limits(widget._ax, expected_x, expected_y)

    widget._sym_check.setChecked(False)
    _assert_limits(widget._ax, expected_x, expected_y)
    viewer.close()


def test_switching_back_to_cached_mode_keeps_its_manual_view(qapp) -> None:
    viewer = _viewer()
    stack = viewer._plot_widget
    stack._ax.set_xlim(-0.6, 0.4)
    stack._ax.set_ylim(2.0, 6.0)
    stack_x = stack._ax.get_xlim()
    stack_y = stack._ax.get_ylim()

    viewer._set_mode("colormap")
    colormap = viewer._plot_widget
    colormap._ax.set_xlim(-0.9, 0.9)
    colormap._ax.set_ylim(11.0, 29.0)
    cmap_x = colormap._ax.get_xlim()
    cmap_y = colormap._ax.get_ylim()

    viewer._set_mode("stack")
    _assert_limits(viewer._plot_widget._ax, stack_x, stack_y)

    viewer._set_mode("colormap")
    _assert_limits(viewer._plot_widget._ax, cmap_x, cmap_y)
    viewer.close()


def test_display_factor_change_transforms_current_viewport(qapp) -> None:
    viewer = _viewer()
    ax = viewer._plot_widget._ax
    ax.set_xlim(-0.5, 0.25)
    ax.set_ylim(2.0, 6.0)

    viewer.update_axes_config({"x_factor": 1e3})
    _assert_limits(viewer._plot_widget._ax, (-500.0, 250.0), (2.0, 6.0))

    viewer.update_axes_config({"y_factor": 1e-3})
    _assert_limits(viewer._plot_widget._ax, (-500.0, 250.0), (0.002, 0.006))

    cfg = viewer._runtime_scene.active_axes.extra[
        "axes_config_by_mode"]["stack"]
    assert cfg["xlim"] == pytest.approx([-500.0, 250.0])
    assert cfg["ylim"] == pytest.approx([0.002, 0.006])
    viewer.close()
