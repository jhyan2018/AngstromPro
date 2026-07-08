# -*- coding: utf-8 -*-
"""
Channel Manager dialog — Edit → Channel Manager…

Left panel: format selector (one entry per registered format that has a
FormatChannelConfig).

Right panel: table of logical channels for the selected format.
  Columns: Display name | Load by default | Aliases (semicolon-separated)
  Actions: Add channel row, Remove selected row, move Up/Down, Save.

Changes are written to AppContext.channel_manager via save_format().
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtCore, QtWidgets
from angstrompro.io.channel_manager import ChannelConfig
from angstrompro.gui.dialogs.persistent_dialog import PersistentDialog

if TYPE_CHECKING:
    from angstrompro.app.context import AppContext


class ChannelManagerDialog(PersistentDialog):

    _settings_key = "ChannelManagerDialog"

    def __init__(self, context: "AppContext", parent=None) -> None:
        super().__init__(parent, default_size=(760, 480))
        self.setWindowTitle("Channel Manager")
        self._cm = context.channel_manager
        self._dirty = False

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        root = QtWidgets.QHBoxLayout()
        root.setSpacing(8)
        outer.addLayout(root)

        # ── Left: format list ─────────────────────────────────────────
        left = QtWidgets.QVBoxLayout()
        fmt_label = QtWidgets.QLabel("Format")
        fmt_label.setObjectName("pref_section_header_label")
        left.addWidget(fmt_label)

        self._fmt_list = QtWidgets.QListWidget()
        self._fmt_list.setFixedWidth(180)
        for fmt_id in self._cm.all_format_ids():
            self._fmt_list.addItem(fmt_id)
        self._fmt_list.currentRowChanged.connect(self._on_format_selected)
        left.addWidget(self._fmt_list)
        root.addLayout(left)

        # ── Right: channel table + buttons ────────────────────────────
        right = QtWidgets.QVBoxLayout()

        self._auto_load_cb = QtWidgets.QCheckBox("Auto-load default channels (skip dialog)")
        self._auto_load_cb.stateChanged.connect(lambda: setattr(self, "_dirty", True))
        right.addWidget(self._auto_load_cb)

        self._table = QtWidgets.QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Display name", "Default", "Aliases  (semicolon-separated)"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.itemChanged.connect(self._on_table_changed)
        right.addWidget(self._table)

        # Row action buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_add    = QtWidgets.QPushButton("Add channel")
        btn_remove = QtWidgets.QPushButton("Remove")
        btn_up     = QtWidgets.QPushButton("↑")
        btn_down   = QtWidgets.QPushButton("↓")
        btn_add.clicked.connect(self._on_add_row)
        btn_remove.clicked.connect(self._on_remove_row)
        btn_up.clicked.connect(self._on_move_up)
        btn_down.clicked.connect(self._on_move_down)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addStretch()
        btn_row.addWidget(btn_up)
        btn_row.addWidget(btn_down)
        right.addLayout(btn_row)

        root.addLayout(right)

        # ── Dialog buttons ────────────────────────────────────────────
        dlg_btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save |
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        dlg_btns.button(QtWidgets.QDialogButtonBox.StandardButton.Save).clicked.connect(self._on_save)
        dlg_btns.button(QtWidgets.QDialogButtonBox.StandardButton.Close).clicked.connect(self.close)
        outer.addWidget(dlg_btns)

        if self._fmt_list.count():
            self._fmt_list.setCurrentRow(0)

    # ------------------------------------------------------------------

    def _on_format_selected(self, row: int) -> None:
        if row < 0:
            return
        fmt_id = self._fmt_list.item(row).text()
        fmt_cfg = self._cm.get(fmt_id)
        self._load_table(
            fmt_cfg.channels if fmt_cfg else [],
            fmt_cfg.auto_load if fmt_cfg else False,
        )

    def _load_table(self, channels: list[ChannelConfig], auto_load: bool = False) -> None:
        self._auto_load_cb.blockSignals(True)
        self._auto_load_cb.setChecked(auto_load)
        self._auto_load_cb.blockSignals(False)
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for cc in channels:
            self._add_table_row(cc.display_name, cc.load_by_default, cc.aliases)
        self._table.blockSignals(False)
        self._dirty = False

    def _add_table_row(self, name: str, default: bool, aliases: list[str]) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        name_item = QtWidgets.QTableWidgetItem(name)
        self._table.setItem(row, 0, name_item)

        cb_widget = QtWidgets.QWidget()
        cb = QtWidgets.QCheckBox()
        cb.setChecked(default)
        cb.stateChanged.connect(lambda: setattr(self, "_dirty", True))
        lay = QtWidgets.QHBoxLayout(cb_widget)
        lay.addWidget(cb)
        lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(0, 0, 0, 0)
        self._table.setCellWidget(row, 1, cb_widget)

        alias_item = QtWidgets.QTableWidgetItem("; ".join(aliases))
        self._table.setItem(row, 2, alias_item)

    def _on_table_changed(self, _item) -> None:
        self._dirty = True

    def _on_add_row(self) -> None:
        self._table.blockSignals(True)
        self._add_table_row("New channel", False, [])
        self._table.blockSignals(False)
        self._dirty = True

    def _on_remove_row(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)
            self._dirty = True

    def _on_move_up(self) -> None:
        row = self._table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self._table.setCurrentCell(row - 1, self._table.currentColumn())

    def _on_move_down(self) -> None:
        row = self._table.currentRow()
        if row < self._table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self._table.setCurrentCell(row + 1, self._table.currentColumn())

    def _swap_rows(self, a: int, b: int) -> None:
        for col in (0, 2):
            ia = self._table.item(a, col)
            ib = self._table.item(b, col)
            ta = ia.text() if ia else ""
            tb = ib.text() if ib else ""
            if ia: ia.setText(tb)
            if ib: ib.setText(ta)
        # Swap checkboxes
        wa = self._table.cellWidget(a, 1)
        wb = self._table.cellWidget(b, 1)
        ca = wa.findChild(QtWidgets.QCheckBox).isChecked() if wa else False
        cb_ = wb.findChild(QtWidgets.QCheckBox).isChecked() if wb else False
        if wa: wa.findChild(QtWidgets.QCheckBox).setChecked(cb_)
        if wb: wb.findChild(QtWidgets.QCheckBox).setChecked(ca)
        self._dirty = True

    def _collect_channels(self) -> list[ChannelConfig]:
        channels = []
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            cb_w = self._table.cellWidget(row, 1)
            default = cb_w.findChild(QtWidgets.QCheckBox).isChecked() if cb_w else False
            alias_item = self._table.item(row, 2)
            raw = alias_item.text() if alias_item else ""
            aliases = [a.strip() for a in raw.split(";") if a.strip()]
            channels.append(ChannelConfig(name, aliases, default))
        return channels

    def _on_save(self) -> None:
        row = self._fmt_list.currentRow()
        if row < 0:
            return
        fmt_id = self._fmt_list.item(row).text()
        channels = self._collect_channels()
        auto_load = self._auto_load_cb.isChecked()
        self._cm.save_format(fmt_id, channels, auto_load=auto_load)
        self._dirty = False

    def closeEvent(self, event) -> None:
        if self._dirty:
            ans = QtWidgets.QMessageBox.question(
                self, "Unsaved changes",
                "You have unsaved changes. Save before closing?",
                QtWidgets.QMessageBox.StandardButton.Save |
                QtWidgets.QMessageBox.StandardButton.Discard |
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            if ans == QtWidgets.QMessageBox.StandardButton.Save:
                self._on_save()
            elif ans == QtWidgets.QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        super().closeEvent(event)
