from __future__ import annotations

import os
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from angstrompro.core.data.annotation_data import PointSetData
from angstrompro.core.data.uds_data import (
    FFT_DOMAIN_KEY,
    FFT_SOURCE_NAME_KEY,
    FFT_TRANSFORM_KEY,
    UdsDataStru,
)
from angstrompro.core.processes import (
    AnnotationSpec,
    DATA_DOMAIN_RECIPROCAL_SPACE,
    InputSpec,
    ProcessSchema,
    select_compatible_input_items,
)
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


def _items():
    real = WorkspaceItem(UdsDataStru(
        name="image",
        data=np.zeros((1, 16, 16)),
    ))

    def fft(name, *, annotated):
        annotations = (
            {"bragg_peaks": PointSetData(np.asarray([[4.0, 12.0]]))}
            if annotated else {}
        )
        return WorkspaceItem(
            UdsDataStru(
                name=name,
                data=np.zeros((1, 16, 16), dtype=complex),
                info={
                    FFT_DOMAIN_KEY: "reciprocal",
                    FFT_TRANSFORM_KEY: "fft_2d",
                    FFT_SOURCE_NAME_KEY: "image",
                },
            ),
            annotations=annotations,
        )

    return real, fft("image_fft", annotated=False), fft(
        "image_fft_hann", annotated=True
    )


def test_domain_selection_preserves_primary_for_unspecified_processes() -> None:
    real, fft, _ = _items()
    selected = select_compatible_input_items(
        [InputSpec("data", "uds", ndim=3)],
        [real, fft],
        [real, fft],
    )

    assert selected == [real]


def test_reciprocal_process_selects_fft_and_allows_explicit_choice(qapp) -> None:
    del qapp
    real, first_fft, annotated_fft = _items()
    schema = ProcessSchema(
        inputs=[InputSpec(
            "data",
            "uds",
            ndim=3,
            data_domain=DATA_DOMAIN_RECIPROCAL_SPACE,
        )],
        annotations=[AnnotationSpec(
            "bragg_peaks", "bragg_peaks", "point_set", required=True
        )],
    )
    entry = SimpleNamespace(
        name="test.reciprocal",
        label="Reciprocal test",
        description="",
        schema=schema,
    )
    dialog = ProcessParamDialog(
        entry,
        SimpleNamespace(param_history=_NoHistory()),
        input_items=[real, first_fft],
        workspace_items=[real, first_fft, annotated_fft],
    )
    try:
        combo = dialog._input_combos["data"]
        assert combo.isEnabled()
        assert combo.count() == 2
        assert combo.currentData() is first_fft
        assert not dialog._btn_run.isEnabled()

        combo.setCurrentIndex(combo.findText(annotated_fft.name))
        assert dialog.input_items() == [annotated_fft]
        assert dialog._btn_run.isEnabled()
        assert dialog._ann_all_ok
    finally:
        dialog.close()
