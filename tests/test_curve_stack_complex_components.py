from __future__ import annotations

import numpy as np
import pytest

from angstrompro.core.data.uds_data import (
    Axis,
    AxisType,
    FFT_TRANSFORM_KEY,
    UdsDataStru,
)
from angstrompro.gui.widgets.curve_stack.curve_stack_viewer_widget import (
    CurveStackViewerWidget,
)
from angstrompro.gui.widgets.curve_stack.runtime_scene import RuntimeScene
from angstrompro.gui.widgets.scene_plot_renderer import render_axes_spec
from angstrompro.utils.qt_compat import QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _complex_fft() -> UdsDataStru:
    data = 1e-12 * np.array([
        [1.0 + 1.0j, -2.0 + 3.0j, -1.0j, 4.0 + 0.0j],
        [2.0 - 1.0j, 1.0 + 2.0j, -3.0 + 4.0j, -2.0 - 2.0j],
    ])
    return UdsDataStru(
        name="fft_curves",
        data=data,
        axes=[
            Axis(
                values=np.array([0.0, 1.0]),
                label="Curve",
                axis_type=AxisType.INDEX,
            ),
            Axis(
                values=np.linspace(-2.0, 1.0, 4),
                label="Frequency",
                units="1/s",
                axis_type=AxisType.FREQUENCY,
            ),
        ],
        info={
            "column_name": "Signal (A)",
            FFT_TRANSFORM_KEY: "fft_1d",
        },
    )


def _viewer() -> CurveStackViewerWidget:
    viewer = CurveStackViewerWidget(config={}, allow_extract=False)
    viewer.set_runtime_scene(RuntimeScene())
    return viewer


def test_fft_curves_default_to_abs_without_losing_complex_data(qapp) -> None:
    viewer = _viewer()
    source = _complex_fft()

    viewer.add_dataset(source.name, source)

    assert viewer.data_component == "abs"
    assert viewer._component_combo.currentText() == "Abs"
    assert viewer._component_combo.isEnabled()
    np.testing.assert_allclose(
        viewer._datasets[source.name]["y"], np.abs(source.data))
    assert np.iscomplexobj(viewer._datasets[source.name]["uds"].data)

    extracted = viewer._extract_curve(
        viewer._datasets[source.name], 0, source.name)
    assert np.iscomplexobj(extracted.data)
    np.testing.assert_allclose(extracted.data, source.data[0])
    viewer.close()


@pytest.mark.parametrize(
    "component, expected",
    [
        ("real", np.real),
        ("imaginary", np.imag),
        ("abs", np.abs),
        ("phase", np.angle),
    ],
)
def test_curve_viewer_switches_complex_components(qapp, component, expected) -> None:
    viewer = _viewer()
    source = _complex_fft()
    viewer.add_dataset(source.name, source)

    viewer.set_data_component(component)

    entry = viewer._datasets[source.name]
    np.testing.assert_allclose(entry["y"], expected(source.data))
    np.testing.assert_allclose(
        viewer._plot_widget._lines[(source.name, 0)].get_ydata(),
        expected(source.data)[0] * viewer._get_axes_config("stack").y_factor,
    )
    if component == "phase":
        assert entry["y_label"] == "Phase (rad)"
    else:
        assert entry["y_label"] == "Signal (A)"
    viewer.close()


def test_component_switch_uses_independent_display_factors(qapp) -> None:
    viewer = _viewer()
    source = _complex_fft()
    viewer.add_dataset(source.name, source)

    assert viewer._get_axes_config("stack").y_factor == pytest.approx(1e12)
    viewer.set_data_component("phase")
    assert viewer._get_axes_config("stack").y_factor == pytest.approx(1.0)
    viewer.set_data_component("abs")
    assert viewer._get_axes_config("stack").y_factor == pytest.approx(1e12)
    viewer.close()


def test_scene_round_trip_and_renderer_preserve_complex_component(qapp) -> None:
    viewer = _viewer()
    source = _complex_fft()
    viewer.add_dataset(source.name, source)
    viewer.set_data_component("imaginary")
    scene = viewer.save_scene("imaginary FFT")

    assert scene.figure.axes_list[0].extra["data_component"] == "imaginary"

    runtime = RuntimeScene()
    runtime.replace(scene)
    restored = CurveStackViewerWidget(config={}, allow_extract=False)
    restored.set_runtime_scene(runtime)
    restored.restore_scene(scene)
    assert restored.data_component == "imaginary"
    np.testing.assert_allclose(
        restored._datasets[source.name]["y"], np.imag(source.data))

    from matplotlib.figure import Figure

    figure = Figure()
    axes = figure.add_subplot(111)
    render_axes_spec(scene.figure.axes_list[0], axes)
    np.testing.assert_allclose(
        axes.lines[0].get_ydata(),
        np.imag(source.data[0])
        * restored._get_axes_config("stack").y_factor,
    )
    restored.close()
    viewer.close()
