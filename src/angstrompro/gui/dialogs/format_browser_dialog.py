# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

FormatBrowserDialog — read-only table of all file formats supported for
loading and/or saving.  Opened from Help → Supported Formats…
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets


def show_format_browser(parent=None) -> None:
    """Create (or raise) a non-modal Format Browser dialog."""
    dlg = FormatBrowserDialog(parent)
    dlg.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
    dlg.show()
    dlg.raise_()


class FormatBrowserDialog(QtWidgets.QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Supported File Formats")
        self.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.resize(820, 500)
        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # summary label — filled after populate
        self._summary = QtWidgets.QLabel()
        self._summary.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._summary)

        # table
        self._table = QtWidgets.QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Format name", "Extension", "Load", "Save", "Description"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        btn_close = QtWidgets.QPushButton("Close")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

    def _populate(self) -> None:
        from angstrompro.io.angstrom_io import registered_formats, registered_ext_loaders
        from angstrompro.io import formats as _   # noqa: F401 — registers raw-ext readers
        from angstrompro.io import uds_io as _u  # noqa: F401 — registers uds r/w
        from angstrompro.io import scene_io as _s  # noqa: F401 — registers scene r/w

        formats = registered_formats() + registered_ext_loaders()

        self._table.setRowCount(len(formats))
        n_load = n_save = 0
        for r, fi in enumerate(formats):
            self._table.setItem(r, 0, _cell(fi.display_name))
            self._table.setItem(r, 1, _cell(fi.extension))
            self._table.setItem(r, 2, _check_cell(fi.readable))
            self._table.setItem(r, 3, _check_cell(fi.writable))
            self._table.setItem(r, 4, _cell(fi.description))
            if fi.readable:
                n_load += 1
            if fi.writable:
                n_save += 1

        self._summary.setText(
            f"{len(formats)} format(s) registered  ·  "
            f"{n_load} loadable  ·  {n_save} saveable"
        )


# helpers

def _cell(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)
    return item


def _check_cell(flag: bool) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem("✓" if flag else "—")
    item.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignCenter)
    return item
