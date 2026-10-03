from __future__ import annotations

import numpy as np
import pytest

from angstrompro.gui.widgets.ndarray_editor_dialog import NdarrayEditorDialog
from angstrompro.utils.qt_compat import QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_slice_change_saves_old_table_then_displays_new_slice(qapp):
    array = np.arange(12, dtype=np.int64).reshape(2, 2, 3)
    dialog = NdarrayEditorDialog(array, label="data")

    dialog._table.item(0, 0).setText("999")
    dialog._spinboxes[0].setValue(1)

    assert dialog._slice_indices == [1]
    assert dialog._pending[0, 0, 0] == 999
    np.testing.assert_array_equal(dialog._pending[1], array[1])
    assert dialog._table.item(0, 0).text() == str(array[1, 0, 0])
    # Pending edits are not committed to the source array until OK.
    assert array[0, 0, 0] == 0
    dialog.close()


def test_invalid_visible_edit_keeps_current_slice_selected(qapp, monkeypatch):
    array = np.arange(8, dtype=np.int64).reshape(2, 2, 2)
    dialog = NdarrayEditorDialog(array, label="data")
    dialog._table.item(0, 0).setText("not-an-integer")
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: None,
    )

    dialog._spinboxes[0].setValue(1)

    assert dialog._spinboxes[0].value() == 0
    assert dialog._slice_indices == [0]
    assert dialog._table.item(0, 0).text() == "not-an-integer"
    np.testing.assert_array_equal(dialog._pending, array)
    dialog.close()


def test_export_writes_only_displayed_nd_slice_with_pending_edits(
    qapp, tmp_path, monkeypatch,
):
    array = np.arange(48, dtype=np.float64).reshape(2, 3, 2, 4)
    dialog = NdarrayEditorDialog(array, label="measurement/data")
    dialog._spinboxes[0].setValue(1)
    dialog._spinboxes[1].setValue(2)
    dialog._table.item(0, 0).setText("123.5")

    chosen = tmp_path / "chosen_export"
    captured = {}

    def choose_path(_parent, _title, suggested, _filters):
        captured["suggested"] = suggested
        return str(chosen), "Text files (*.txt)"

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        choose_path,
    )

    dialog._export_current_slice()

    output = chosen.with_suffix(".txt")
    exported = np.loadtxt(output, delimiter="\t")
    expected = array[1, 2].copy()
    expected[0, 0] = 123.5
    np.testing.assert_allclose(exported, expected)
    assert captured["suggested"] == "measurement_data_slice_1_2.txt"
    assert "Exported current slice" in dialog._status.text()
    assert array[1, 2, 0, 0] != 123.5
    dialog.close()
