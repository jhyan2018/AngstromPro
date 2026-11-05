"""One schema-backed correction entry, unchanged numerical implementations."""

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from angstrompro.algorithms.lattice.correction import (
    perfect_lattice_hexagonal,
    perfect_lattice_square,
)
from angstrompro.core.data.annotation_data import PointSetData, serialize_annotation
from angstrompro.core.data.base import ProcRecord
from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes import ProcessRegistry, ProcessRunner
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.dialogs.process_param_dialog import ProcessParamDialog
from angstrompro.utils.qt_compat import QtWidgets


PROCESS = "spatial.perfect_lattice_2d"
CORRECTIONS = {
    "hexagonal": perfect_lattice_hexagonal,
    "square": perfect_lattice_square,
}
PADDING = ["constant", "reflect", "edge", "wrap", "symmetric"]


def _source(shape=(2, 64, 64)):
    return UdsDataStru(
        name="original",
        data=np.random.default_rng(42).normal(size=shape),
        axes=[
            Axis(np.arange(shape[0]) * 0.01, "Bias", "V"),
            Axis(np.arange(shape[1]) * 2e-10, "Row", "m"),
            Axis(np.arange(shape[2]) * 3e-10, "Column", "m"),
        ],
        info={"source": "original.uds", "sample": "lattice"},
        proc_history=[ProcRecord("earlier", {"value": 1})],
    )


def _peaks(shape=(2, 64, 64)):
    center = np.array([shape[1] // 2, shape[2] // 2])
    return PointSetData(center + np.array([[7.25, -15.5], [-14.5, -4.25]]))


def test_only_unified_correction_is_registered_with_full_schema():
    registry = ProcessRegistry()
    entries = [
        e
        for e in registry.by_kind("process")
        if e.name.startswith("spatial.perfect_lattice")
    ]
    assert [e.name for e in entries] == [PROCESS]
    entry = entries[0]
    assert entry.label == "Perfect Lattice 2D"
    assert entry.category == "Lattice & Registration"
    assert not registry.has("spatial.perfect_lattice_square_2d")
    assert not registry.has("spatial.perfect_lattice_hexagonal_2d")
    assert registry.get("simulate.perfect_lattice2d").schema.inputs == []
    assert entry in registry.compatible_with("uds", 3)
    assert entry not in registry.compatible_with("uds", 2)
    schema = entry.schema
    assert [(s.name, s.type_id, s.ndim) for s in schema.inputs] == [("data", "uds", 3)]
    assert [(s.type_id, s.ndim) for s in schema.outputs] == [("uds", 3)]
    assert [(s.name, s.role, s.type_id, s.required) for s in schema.annotations] == [
        ("bragg_peaks", "bragg_peaks", "point_set", True)
    ]
    assert schema.defaults() == {
        "lattice_type": "hexagonal",
        "interpolate_method": "bilinear",
        "pad_method": "constant",
    }
    assert schema.get_param("lattice_type").choices == list(CORRECTIONS)
    assert schema.get_param("interpolate_method").choices == ["bilinear"]
    assert schema.get_param("pad_method").choices == PADDING


@pytest.mark.parametrize("lattice_type", CORRECTIONS)
@pytest.mark.parametrize("pad_method", PADDING)
@pytest.mark.parametrize("shape", [(2, 64, 64), (1, 47, 65)])
def test_dispatch_matches_internal_calculation_and_records_choices(
    lattice_type, pad_method, shape
):
    source = _source(shape)
    before = deepcopy(source)
    peaks = _peaks(shape)
    coords_before = peaks.coords.copy()
    coords = peaks.coords
    expected = CORRECTIONS[lattice_type](
        source,
        coords[0, 1],
        coords[0, 0],
        coords[1, 1],
        coords[1, 0],
        "bilinear",
        pad_method,
    )
    result = ProcessRegistry().run(
        PROCESS,
        {"data": source},
        {"lattice_type": lattice_type, "pad_method": pad_method},
        annotations={"bragg_peaks": peaks},
    )
    np.testing.assert_array_equal(result.data, expected.data)
    assert np.isfinite(result.data).all()
    assert result.name == "original_pl"
    assert result.info == source.info
    for actual, wanted in zip(result.axes, expected.axes):
        np.testing.assert_array_equal(actual.values, wanted.values)
        assert (actual.label, actual.units) == (wanted.label, wanted.units)
    assert len(result.proc_history) == len(before.proc_history) + 1
    assert result.proc_history[:-1] == before.proc_history
    record = result.proc_history[-1]
    assert record.step == PROCESS
    assert record.params == {
        "lattice_type": lattice_type,
        "interpolate_method": "bilinear",
        "pad_method": pad_method,
    }
    assert record.annotations == {"bragg_peaks": serialize_annotation(peaks)}
    assert record.input_item_names == [source.name]
    assert source.proc_history == before.proc_history
    np.testing.assert_array_equal(source.data, before.data)
    np.testing.assert_array_equal(peaks.coords, coords_before)
    assert not np.shares_memory(result.data, source.data)


def test_defaults_and_first_two_peaks_preserve_existing_convention():
    registry = ProcessRegistry()
    source = _source()
    peaks = _peaks()
    expected = registry.run(PROCESS, {"data": source}, {}, {"bragg_peaks": peaks})
    more_peaks = PointSetData(np.vstack([peaks.coords, [5, 9], [11, 19]]))
    result = registry.run(
        PROCESS,
        {"data": source},
        {"lattice_type": "hexagonal"},
        {"bragg_peaks": more_peaks},
    )
    np.testing.assert_array_equal(result.data, expected.data)


@pytest.mark.parametrize("pad_method", PADDING)
def test_padding_and_interpolation_match_numpy_reference(pad_method):
    from angstrompro.algorithms.pixel_interpolation import PixelInterpolation

    source = np.arange(12, dtype=float).reshape(3, 4)
    x = np.array([[-1.25, 1.5, 4.25]])
    y = np.array([[-0.5, 0.75, 3.5]])
    interpolation = PixelInterpolation(source, x, y, pad_method=pad_method)
    reference = np.pad(source, 8, mode=pad_method)
    expected = np.zeros_like(x)
    # Explicit four-neighbour sum independent of the vectorised implementation.
    for index in np.ndindex(x.shape):
        col, row = int(np.floor(x[index])), int(np.floor(y[index]))
        dx, dy = x[index] - col, y[index] - row
        for r, wy in ((row, 1 - dy), (row + 1, dy)):
            for c, wx in ((col, 1 - dx), (col + 1, dx)):
                expected[index] += wx * wy * reference[r + 8, c + 8]
    np.testing.assert_allclose(interpolation.dataMapping(), expected)


@pytest.mark.parametrize(
    "params, message",
    [
        ({"lattice_type": "triangular"}, "Lattice type"),
        ({"lattice_type": None}, "Lattice type"),
        ({"interpolate_method": "nearest"}, "Interpolation"),
        ({"pad_method": "typo"}, "Padding"),
    ],
)
def test_invalid_choices_are_rejected_for_non_gui_callers(params, message):
    with pytest.raises(ValueError, match=message):
        ProcessRegistry().run(
            PROCESS, {"data": _source()}, params, {"bragg_peaks": _peaks()}
        )


@pytest.mark.parametrize(
    "peaks, message",
    [
        (None, "requires a 'bragg_peaks'"),
        (object(), "must be a point set"),
        (PointSetData(), "at least 2"),
        (PointSetData(np.array([[1, 2]])), "at least 2"),
        (PointSetData(np.ones((2, 3))), "at least 2"),
        (PointSetData(np.array([[1, np.nan], [2, 3]])), "finite"),
    ],
)
def test_invalid_annotations_fail_clearly(peaks, message):
    with pytest.raises(ValueError, match=message):
        ProcessRegistry().run(PROCESS, {"data": _source()}, {}, {"bragg_peaks": peaks})


def test_rejects_non_stack_input():
    with pytest.raises(ValueError, match="requires ndim=3"):
        ProcessRegistry().run(
            PROCESS,
            {"data": UdsDataStru.from_array(np.ones((8, 8)), "image")},
            {},
            {"bragg_peaks": _peaks()},
        )


def test_manual_dialog_and_runner_use_same_annotation_owner_and_choices():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    item = WorkspaceItem(_source(), annotations={"bragg_peaks": _peaks()})
    registry = ProcessRegistry()
    entry = registry.get(PROCESS)
    context = SimpleNamespace(
        param_history=SimpleNamespace(get=lambda _name, defaults: defaults)
    )
    dialog = ProcessParamDialog(
        entry, context, input_items=[item], workspace_items=[item]
    )
    try:
        assert app is not None
        assert dialog._ann_all_ok
        for name, choices in {
            "lattice_type": list(CORRECTIONS),
            "interpolate_method": ["bilinear"],
            "pad_method": PADDING,
        }.items():
            editor = dialog._widgets[name]
            assert isinstance(editor, QtWidgets.QComboBox)
            assert not editor.isEditable()
            assert [editor.itemData(i) for i in range(editor.count())] == choices
        lattice = dialog._widgets["lattice_type"]
        lattice.setCurrentIndex(lattice.findData("square"))
        assert dialog.params()["lattice_type"] == "square"
        annotations = ProcessRunner._build_annotations(entry, [item])
        assert annotations["bragg_peaks"] is item.annotations["bragg_peaks"]
        result = registry.run(
            PROCESS, {"data": item.payload}, dialog.params(), annotations
        )
        assert result.proc_history[-1].params["lattice_type"] == "square"
    finally:
        dialog.close()
