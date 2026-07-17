# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

FormatBrowserDialog — read-only table of all file formats supported for
loading and/or saving.  Opened from Help → Supported Formats…
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets
from angstrompro.gui.dialogs.persistent_dialog import PersistentDialog


def show_format_browser(parent=None) -> None:
    """Create (or raise) a non-modal Format Browser dialog."""
    dlg = FormatBrowserDialog(parent)
    dlg.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
    dlg.show()
    dlg.raise_()


class FormatBrowserDialog(PersistentDialog):

    _settings_key = "FormatBrowserDialog"

    def __init__(self, parent=None) -> None:
        super().__init__(parent, default_size=(820, 500))
        self.setWindowTitle("Supported File Formats")
        self.setWindowModality(QtCore.Qt.WindowModality.NonModal)
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
        layout.addWidget(self._summary, 0)

        # inner widget for scroll area
        inner = QtWidgets.QWidget()
        inner.setMinimumWidth(600)
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        self._table = _AutoHeightTable(5)
        self._table.setHorizontalHeaderLabels(
            ["Format name", "Extension", "Load", "Save", "Description"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hh.setDefaultAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            if hasattr(QtCore.Qt.AlignmentFlag, "AlignLeft")
            else QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(True)
        self._table.setStyleSheet(
            "QTableWidget { border: 1px solid palette(mid); }"
            "QTableWidget::item { padding: 4px 8px; }"
            "QHeaderView::section { padding: 4px 8px; }"
            "QScrollBar:vertical { width: 0px; }"
            "QScrollBar:horizontal { height: 0px; }"
        )
        self._table.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            if hasattr(QtCore.Qt.ScrollBarPolicy, "ScrollBarAlwaysOff")
            else QtCore.Qt.ScrollBarAlwaysOff)
        self._table.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            if hasattr(QtCore.Qt.ScrollBarPolicy, "ScrollBarAlwaysOff")
            else QtCore.Qt.ScrollBarAlwaysOff)
        inner_layout.addWidget(self._table)
        inner_layout.addStretch()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame
                             if hasattr(QtWidgets.QFrame.Shape, "NoFrame")
                             else QtWidgets.QFrame.NoFrame)
        layout.addWidget(scroll, 1)

        btn_close = QtWidgets.QPushButton("Close")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row, 0)

    def _populate(self) -> None:
        from angstrompro.io.angstrom_io import registered_formats, registered_ext_loaders
        from angstrompro.io import formats as _    # noqa: F401
        from angstrompro.io import uds_io as _u   # noqa: F401
        from angstrompro.io import scene_plot_io as _s  # noqa: F401

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
        QtCore.QTimer.singleShot(0, self._refit_rows)

    def _refit_rows(self) -> None:
        self._table.resizeRowsToContents()
        self._table.updateGeometry()


# ---------------------------------------------------------------------------
# Auto-height table — expands to show all rows, word-wraps description column
# ---------------------------------------------------------------------------

class _AutoHeightTable(QtWidgets.QTableWidget):

    def __init__(self, cols: int, parent=None):
        super().__init__(0, cols, parent)

    def sizeHint(self) -> QtCore.QSize:
        frame = self.frameWidth() * 2
        h = self.horizontalHeader().height() + frame
        for i in range(self.rowCount()):
            h += self.rowHeight(i)
        return QtCore.QSize(super().sizeHint().width(), h)

    def minimumSizeHint(self) -> QtCore.QSize:
        return self.sizeHint()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QtCore.QTimer.singleShot(0, lambda: (
            self.resizeRowsToContents(), self.updateGeometry()))


# ---------------------------------------------------------------------------
# Cell helpers
# ---------------------------------------------------------------------------

def _cell(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)
    return item


def _check_cell(flag: bool) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem("✓" if flag else "—")
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    return item
