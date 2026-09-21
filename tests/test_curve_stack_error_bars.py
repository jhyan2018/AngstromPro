from __future__ import annotations

import numpy as np
import pytest

from angstrompro.core.data.scene_plot import (
    ArtistSpec,
    AxesConfig,
    AxesSpec,
    ErrorBarStyle,
    FigureConfig,
    LineStyle,
    ScenePlot,
)
from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.gui.widgets.curve_stack.curve_stack_viewer_widget import (
    CurveStackViewerWidget,
)
from angstrompro.gui.widgets.curve_stack.axes_config_panel import AxesConfigPanel
from angstrompro.gui.widgets.curve_stack.prepare import (
    prepare_entry,
    prepare_y_error,
)
from angstrompro.gui.widgets.curve_stack.runtime_scene import RuntimeScene
from angstrompro.gui.widgets.curve_stack.si_scale import (
    factor_prefix,
    scaled_axis_label,
    si_scale,
)
from angstrompro.gui.widgets.scene_plot_renderer import render_axes_spec
from angstrompro.io import scene_plot_io
from angstrompro.utils.qt_compat import QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _curve(name: str, data, *, axis=None) -> UdsDataStru:
    values = np.asarray(data, dtype=float)
    if axis is None:
        axis = np.linspace(-1.0, 1.0, values.shape[-1])
    axes = []
    if values.ndim == 2:
        axes.append(Axis(
            values=np.arange(values.shape[0], dtype=float),
            label="Curve",
            axis_type=AxisType.INDEX,
        ))
    axes.append(Axis(
        values=np.asarray(axis, dtype=float),
        label="Bias",
        units="V",
        axis_type=AxisType.BIAS,
    ))
    return UdsDataStru(
        name=name,
        data=values,
        axes=axes,
        info={"column_name": "Current (A)"},
    )


def test_y_values_and_errors_remain_in_original_units() -> None:
    target = _curve("signal", [1e-9, 2e-9, 3e-9])
    errors = _curve("sigma", [1e-10, 2e-10, 3e-10])
    entry = prepare_entry("signal", target)

    scaled = prepare_y_error(errors, entry)

    np.testing.assert_allclose(entry["y"], [[1e-9, 2e-9, 3e-9]])
    np.testing.assert_allclose(scaled, [[1e-10, 2e-10, 3e-10]])
    assert entry["y_label"] == "Current (A)"
    assert entry["y_scale"] == pytest.approx(1.0)


def test_prepared_3ds_curve_uses_raw_channel_units_in_label() -> None:
    curve = _curve("didv", [1e-12, 2e-12, 3e-12])
    curve.info = {
        "channel_display_name": "dI/dV",
        "channel_loaded": "LI Demod 1 X (A)",
    }

    entry = prepare_entry("didv", curve)

    assert entry["y_label"] == "dI/dV (A)"


def test_axis_factor_prefixes_and_auto_range_are_bounded() -> None:
    assert factor_prefix(1e-12) == "T"
    assert factor_prefix(1.0) == ""
    assert factor_prefix(1e3) == "m"
    assert factor_prefix(1e12) == "p"
    assert factor_prefix(1e18) == "a"
    assert scaled_axis_label("Bias (V)", "V", 1e3) == "Bias (mV)"
    assert si_scale(np.array([1e-30])) == ("a", 1e18)
    assert si_scale(np.array([1e30])) == ("T", 1e-12)


@pytest.mark.parametrize(
    "errors, message",
    [
        (_curve("wrong shape", [0.1, 0.2]), "shape must match"),
        (_curve("negative", [0.1, -0.2, 0.3]), "cannot be negative"),
        (_curve("wrong axis", [0.1, 0.2, 0.3], axis=[0, 1, 2]),
         "axis values must match"),
    ],
)
def test_y_error_validation_rejects_incompatible_data(errors, message) -> None:
    entry = prepare_entry("signal", _curve("signal", [1.0, 2.0, 3.0]))

    with pytest.raises(ValueError, match=message):
        prepare_y_error(errors, entry)


def test_viewer_renders_and_removes_symmetric_y_errors(qapp) -> None:
    runtime = RuntimeScene()
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    viewer.set_runtime_scene(runtime)
    viewer.add_dataset("signal", _curve("signal", [1.0, 2.0, 3.0]))

    viewer.set_y_error_data(
        "signal",
        _curve("sigma", [0.1, 0.2, 0.3]),
        capsize=4.0,
        linewidth=1.5,
        errorevery=2,
    )

    spec = runtime.active_axes.artists[0]
    assert spec.errorbar is not None
    assert spec.errorbar.yerr_data.name == "sigma"
    assert viewer._datasets["signal"]["yerr"].shape == (1, 3)
    assert ("signal", 0) in viewer._plot_widget._errorbars
    assert "Y±" in viewer._tree.topLevelItem(0).text(0)
    assert viewer._plot_widget._ax.yaxis.get_major_formatter().get_useOffset() is False

    saved = viewer.save_scene("with-errors")
    restored_runtime = RuntimeScene()
    restored_runtime.replace(saved)
    restored_viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    restored_viewer.set_runtime_scene(restored_runtime)
    restored_viewer.restore_scene(restored_runtime.scene)
    assert restored_viewer.get_y_error_style("signal") is not None
    assert ("signal", 0) in restored_viewer._plot_widget._errorbars

    viewer.remove_y_error_data("signal")

    assert spec.errorbar is None
    assert "yerr" not in viewer._datasets["signal"]
    assert not viewer._plot_widget._errorbars
    restored_viewer.close()
    viewer.close()


def test_viewer_persists_and_applies_axis_factors_for_pico_scale_data(qapp) -> None:
    runtime = RuntimeScene()
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    viewer.set_runtime_scene(runtime)
    signal = _curve("signal", [1.0e-12, 2.0e-12, 3.0e-12])
    viewer.add_dataset("signal", signal)
    viewer.set_y_error_data(
        "signal", _curve("sigma", [0.1e-12, 0.2e-12, 0.3e-12]))

    viewer._plot_widget._canvas.draw()

    plotted = viewer._plot_widget._lines[("signal", 0)].get_ydata()
    np.testing.assert_allclose(plotted, [1.0, 2.0, 3.0])
    mode_config = runtime.active_axes.extra["axes_config_by_mode"]["stack"]
    assert mode_config["y_factor"] == pytest.approx(1e12)
    assert viewer._plot_widget._ax.get_ylabel() == "Current (pA)"
    segments = viewer._plot_widget._errorbars[("signal", 0)].lines[2][0].get_segments()
    np.testing.assert_allclose(segments[0][:, 1], [0.9, 1.1])
    multiplier = viewer._plot_widget._ax.yaxis.get_offset_text().get_text()
    assert multiplier == ""

    saved = viewer.save_scene("scaled")
    assert saved.figure.axes_list[0].extra[
        "axes_config_by_mode"]["stack"]["y_factor"] == pytest.approx(1e12)
    viewer.close()


def test_viewer_applies_x_factor_without_duplicating_axis_units(qapp) -> None:
    runtime = RuntimeScene()
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    viewer.set_runtime_scene(runtime)
    signal = _curve(
        "signal", [1.0, 2.0, 3.0],
        axis=[-2.1e-3, -1.0e-3, 0.1e-3],
    )
    signal.axes[-1].label = "Bias (V)"
    viewer.add_dataset("signal", signal)

    plotted = viewer._plot_widget._lines[("signal", 0)].get_xdata()

    np.testing.assert_allclose(plotted, [-2.1, -1.0, 0.1])
    mode_config = runtime.active_axes.extra["axes_config_by_mode"]["stack"]
    assert mode_config["x_factor"] == pytest.approx(1e3)
    assert viewer._plot_widget._ax.get_xlabel() == "Bias (mV)"
    viewer.close()


def test_axes_panel_shows_and_edits_scene_factors(qapp) -> None:
    runtime = RuntimeScene()
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    viewer.set_runtime_scene(runtime)
    viewer.add_dataset(
        "signal",
        _curve(
            "signal", [1.0e-12, 2.0e-12, 3.0e-12],
            axis=[-2.0e-3, 0.0, 2.0e-3],
        ),
    )
    panel = AxesConfigPanel()
    panel.set_scene_config_provider(viewer._current_mode_cfg)
    panel.config_changed.connect(viewer.update_axes_config)
    panel.bind_context(viewer.view_context)

    assert float(panel._xfactor.currentData()) == pytest.approx(1e3)
    assert float(panel._yfactor.currentData()) == pytest.approx(1e12)

    viewer.update_axes_config({"ylim": [0.0, 4.0]})
    panel._yfactor.setCurrentIndex(panel._yfactor.findData(1e9))

    config = runtime.active_axes.extra["axes_config_by_mode"]["stack"]
    assert config["y_factor"] == pytest.approx(1e9)
    assert config["ylim"] == pytest.approx([0.0, 0.004])
    plotted = viewer._plot_widget._lines[("signal", 0)].get_ydata()
    np.testing.assert_allclose(plotted, [1e-3, 2e-3, 3e-3])
    assert viewer._plot_widget._ax.get_ylabel() == "Current (nA)"
    panel.close()
    viewer.close()


def test_open_axes_panel_refreshes_factors_when_first_dataset_is_added(qapp) -> None:
    """Match the module order: construct/bind the dock before loading data."""
    runtime = RuntimeScene()
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    viewer.set_runtime_scene(runtime)
    panel = AxesConfigPanel()
    panel.bind_context(viewer.view_context)
    panel.set_scene_config_provider(viewer._current_mode_cfg)

    assert float(panel._xfactor.currentData()) == pytest.approx(1.0)
    assert float(panel._yfactor.currentData()) == pytest.approx(1.0)

    viewer.add_dataset(
        "signal",
        _curve(
            "signal", [1.0e-12, 2.0e-12, 3.0e-12],
            axis=[-2.0e-3, 0.0, 2.0e-3],
        ),
    )

    assert float(panel._xfactor.currentData()) == pytest.approx(1e3)
    assert float(panel._yfactor.currentData()) == pytest.approx(1e12)
    panel.close()
    viewer.close()


def test_scene_plot_round_trip_preserves_attached_error_uds(tmp_path) -> None:
    signal = _curve("signal", [1.0, 2.0, 3.0])
    errors = _curve("sigma", [0.1, 0.2, 0.3])
    scene = ScenePlot(
        name="error-scene",
        figure=FigureConfig(axes_list=[AxesSpec(
            config=AxesConfig(x_factor=1e3, y_factor=1e12),
            artists=[ArtistSpec(
            kind="line",
            style=LineStyle(),
            errorbar=ErrorBarStyle(
                yerr_data=errors,
                capsize=3.0,
                linewidth=1.2,
                errorevery=2,
            ),
            data=signal,
            label="signal",
        )])]),
    )
    path = tmp_path / "error-scene.scplot"

    scene_plot_io.save(path, scene)
    restored = scene_plot_io.load(path)

    style = restored.figure.axes_list[0].artists[0].errorbar
    assert style is not None
    assert style.capsize == pytest.approx(3.0)
    assert style.errorevery == 2
    np.testing.assert_array_equal(style.yerr_data.data, errors.data)
    restored_config = restored.figure.axes_list[0].config
    assert restored_config.x_factor == pytest.approx(1e3)
    assert restored_config.y_factor == pytest.approx(1e12)


def test_standalone_scene_renderer_draws_attached_errors() -> None:
    from matplotlib.figure import Figure

    signal = _curve("signal", [1.0e-12, 2.0e-12, 3.0e-12])
    errors = _curve("sigma", [0.1e-12, 0.2e-12, 0.3e-12])
    axes_spec = AxesSpec(
        artists=[ArtistSpec(
            kind="line",
            style=LineStyle(),
            errorbar=ErrorBarStyle(yerr_data=errors, capsize=2.0),
            data=signal,
            label="signal",
        )],
        extra={"axes_config_by_mode": {
            "stack": {"x_factor": 1.0, "y_factor": 1e12},
        }},
    )
    axes = Figure().add_subplot(111)

    render_axes_spec(axes_spec, axes)

    assert len(axes.lines) == 3  # central line plus two cap lines
    assert len(axes.collections) == 1  # vertical error segments
    np.testing.assert_allclose(axes.lines[0].get_ydata(), [1.0, 2.0, 3.0])
    segments = axes.collections[0].get_segments()
    np.testing.assert_allclose(segments[0][:, 1], [0.9, 1.1])
    assert axes.get_ylabel() == "Current (pA)"
