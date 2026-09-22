from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from angstrompro.core.processes.param_schema import (
    InputSpec,
    MetricOutputSpec,
    ParameterSpec,
    ProcessSchema,
)
from angstrompro.core.processes.process_entry import ProcessEntry
from angstrompro.gui.dialogs.process_browser_dialog import ProcessBrowserDialog
from angstrompro.utils.qt_compat import IS_QT6, QtWidgets


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class _Registry:
    def __init__(self, entry: ProcessEntry) -> None:
        self._entry = entry

    def by_category(self) -> dict[str, list[ProcessEntry]]:
        return {self._entry.category: [self._entry]}

    def get(self, name: str) -> ProcessEntry:
        if name != self._entry.name:
            raise KeyError(name)
        return self._entry


def _entry() -> ProcessEntry:
    return ProcessEntry(
        name="test.example",
        label="Example Process",
        category="Test",
        description="Used to exercise process selection.",
        func=lambda inputs, params: inputs,
        schema=ProcessSchema(
            inputs=[InputSpec("data", "uds")],
            params=[ParameterSpec("mode", str, "fast", choices=["fast", "exact"])],
            metric_outputs=[MetricOutputSpec(
                "quality_score",
                label="Quality Score",
                units="a.u.",
                description="Scalar quality available to workflow conditions.",
            )],
        ),
    )


def test_process_browser_selection_mode_returns_selected_entry(qapp) -> None:
    del qapp
    entry = _entry()
    context = SimpleNamespace(processes=_Registry(entry))
    dialog = ProcessBrowserDialog(
        context,
        selection_mode=True,
        accept_label="Add process",
        title="Add Registered Process",
    )

    assert dialog.windowTitle() == "Add Registered Process"
    assert dialog._select_button.text() == "Add process"
    assert not dialog._select_button.isEnabled()
    assert dialog.selected_entry() is None

    process_item = dialog._tree.topLevelItem(0).child(0)
    dialog._tree.setCurrentItem(process_item)

    assert dialog.selected_entry() is entry
    assert dialog._select_button.isEnabled()
    assert dialog._tbl_metrics.rowCount() == 1
    assert [
        dialog._tbl_metrics.item(0, column).text()
        for column in range(4)
    ] == [
        "quality_score",
        "Quality Score",
        "a.u.",
        "Scalar quality available to workflow conditions.",
    ]

    dialog._select_button.click()
    accepted = (
        QtWidgets.QDialog.DialogCode.Accepted
        if IS_QT6 else QtWidgets.QDialog.Accepted
    )
    assert dialog.result() == accepted
    dialog.close()


def test_process_browser_default_mode_remains_browse_only(qapp) -> None:
    del qapp
    context = SimpleNamespace(processes=_Registry(_entry()))
    dialog = ProcessBrowserDialog(context)

    assert dialog.windowTitle() == "Process Browser"
    assert dialog._select_button is None
    assert dialog._button_box.button(
        QtWidgets.QDialogButtonBox.StandardButton.Close
    ) is not None
    dialog.close()
