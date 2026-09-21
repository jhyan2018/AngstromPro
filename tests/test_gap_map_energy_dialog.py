"""Gap Map energy controls derive physical limits from the staged UDS axis."""

from __future__ import annotations

import os
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from angstrompro.core.data.uds_data import Axis, UdsDataStru
from angstrompro.core.processes.registry import ProcessRegistry
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.gui.dialogs.process_param_dialog import ProcessParamDialog
from angstrompro.utils.qt_compat import QtWidgets


class _NoHistory:
    def get(self, _process_name: str, defaults: dict) -> dict:
        return dict(defaults)

    def save(self, _process_name: str, _params: dict) -> None:
        pass


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_gap_map_dialog_uses_staged_energy_axis_values_and_units(qapp) -> None:
    del qapp
    energies = np.array([2.0, 1.5, 1.0, 0.5], dtype=np.float64)
    payload = UdsDataStru(
        name="descending-bias",
        data=np.zeros((4, 2, 2), dtype=np.float64),
        axes=[
            Axis(values=energies, label="Bias", units="mV"),
            Axis(values=np.arange(2), label="Y"),
            Axis(values=np.arange(2), label="X"),
        ],
    )
    item = WorkspaceItem(payload)
    entry = ProcessRegistry().get("spectral.gap_map_2d")
    context = SimpleNamespace(param_history=_NoHistory())

    dialog = ProcessParamDialog(
        entry,
        context,
        input_items=[item],
        workspace_items=[item],
    )
    try:
        minimum = dialog._widgets["energy_min"]
        maximum = dialog._widgets["energy_max"]
        assert minimum.minimum() == pytest.approx(0.5)
        assert minimum.maximum() == pytest.approx(2.0)
        assert minimum.value() == pytest.approx(0.5)
        assert maximum.minimum() == pytest.approx(0.5)
        assert maximum.maximum() == pytest.approx(2.0)
        assert maximum.value() == pytest.approx(2.0)
        assert minimum.singleStep() == pytest.approx(0.5)

        labels = [label.text() for label in dialog.findChildren(QtWidgets.QLabel)]
        assert "Energy minimum  (mV):" in labels
        assert "Energy maximum  (mV):" in labels
        assert set(dialog.params()) == {"order", "energy_min", "energy_max"}
    finally:
        dialog.close()
