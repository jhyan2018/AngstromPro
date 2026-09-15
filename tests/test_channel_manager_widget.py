from __future__ import annotations

import os
from copy import deepcopy
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from angstrompro.gui.widgets.channel_manager_widget import ChannelManagerWidget
from angstrompro.gui.widgets.preferences import (
    PrefItem,
    PrefSection,
    PreferencesPanel,
)
from angstrompro.io.channel_manager import ChannelConfig, FormatChannelConfig
from angstrompro.utils.qt_compat import QtWidgets


class _ChannelManagerStub:
    def __init__(self) -> None:
        self.formats = {
            "nanonis_3ds": FormatChannelConfig(
                "nanonis_3ds",
                [ChannelConfig("dI/dV", ["LI Demod"], True)],
                False,
            ),
            "nanonis_sxm": FormatChannelConfig(
                "nanonis_sxm",
                [ChannelConfig("Z", ["Z (m)"], True)],
                False,
            ),
        }
        self.updated: dict[str, FormatChannelConfig] = {}

    def all_format_ids(self) -> list[str]:
        return list(self.formats)

    def get(self, format_id: str) -> FormatChannelConfig | None:
        return self.formats.get(format_id)

    def update_format(
        self,
        format_id: str,
        channels: list[ChannelConfig],
        auto_load: bool = False,
    ) -> None:
        config = FormatChannelConfig(
            format_id,
            deepcopy(channels),
            auto_load,
        )
        self.formats[format_id] = config
        self.updated[format_id] = config


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _default_checkbox(widget: ChannelManagerWidget, row: int = 0):
    container = widget._table.cellWidget(row, 1)
    return container.findChild(QtWidgets.QCheckBox)


def test_switching_formats_preserves_all_drafts_until_apply(qapp) -> None:
    del qapp
    manager = _ChannelManagerStub()
    widget = ChannelManagerWidget(
        context=SimpleNamespace(channel_manager=manager)
    )

    assert widget._fmt_list.currentItem().text() == "nanonis_3ds"
    _default_checkbox(widget).setChecked(False)
    widget._auto_load_cb.setChecked(True)

    widget._fmt_list.setCurrentRow(1)
    _default_checkbox(widget).setChecked(False)

    widget._fmt_list.setCurrentRow(0)
    assert not _default_checkbox(widget).isChecked()
    assert widget._auto_load_cb.isChecked()

    widget._fmt_list.setCurrentRow(1)
    assert not _default_checkbox(widget).isChecked()
    assert manager.updated == {}

    widget.get_value()

    assert set(manager.updated) == {"nanonis_3ds", "nanonis_sxm"}
    assert not manager.updated["nanonis_3ds"].channels[0].load_by_default
    assert manager.updated["nanonis_3ds"].auto_load
    assert not manager.updated["nanonis_sxm"].channels[0].load_by_default
    widget.close()


def test_channel_manager_labels_explain_the_two_default_levels(qapp) -> None:
    del qapp
    widget = ChannelManagerWidget(
        context=SimpleNamespace(channel_manager=_ChannelManagerStub())
    )

    assert widget._table.horizontalHeaderItem(1).text() == "Load by default"
    assert "for this format" in widget._auto_load_cb.text()
    assert "skip selection dialog" in widget._auto_load_cb.text()
    assert "Unmatched defaults" in widget._auto_load_cb.toolTip()
    widget.close()


def test_3ds_source_choice_is_kept_in_preferences_draft(qapp) -> None:
    del qapp
    manager = _ChannelManagerStub()
    widget = ChannelManagerWidget(
        context=SimpleNamespace(channel_manager=manager)
    )
    source_combo = widget._table.cellWidget(0, 2)
    assert source_combo.isEnabled()
    source_combo.setCurrentIndex(source_combo.findData("experiment_parameter"))
    widget._fmt_list.setCurrentRow(1)
    assert not widget._table.cellWidget(0, 2).isEnabled()
    widget._fmt_list.setCurrentRow(0)
    assert widget._table.cellWidget(0, 2).currentData() == "experiment_parameter"

    widget.get_value()

    assert manager.updated["nanonis_3ds"].channels[0].source == "experiment_parameter"
    widget.close()


def test_reset_updates_visible_values_and_can_be_saved(qapp) -> None:
    del qapp
    applied: list[dict] = []
    saved: list[dict] = []
    panel = PreferencesPanel(
        module_name="Example",
        schema=[PrefSection("Values", "settings", [
            PrefItem("count", "Count", "integer"),
        ])],
        config={"count": 7},
        on_apply=applied.append,
        on_save_as_default=saved.append,
        on_reset=lambda: {"count": 3},
    )
    control = panel._controls[0][1]

    panel._on_reset()

    assert control.value() == 3
    assert panel._config == {"count": 3}

    panel._on_save_as_default()

    assert applied[-1] == {"count": 3}
    assert saved[-1] == {"count": 3}
    panel.close()
