# -*- coding: utf-8 -*-
"""
PluginListWidget — editable list of {path, module} plugin entries for the
Preferences → Plugins panel.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets


class _PluginRow(QtWidgets.QWidget):
    """One row: [path line-edit] [browse] [module line-edit] [remove]"""

    remove_requested = QtCore.Signal()

    def __init__(self, path: str = "", module: str = "", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._path_edit = QtWidgets.QLineEdit(path)
        self._path_edit.setPlaceholderText("src/ folder path")
        self._path_edit.setMinimumWidth(200)

        browse_btn = QtWidgets.QToolButton()
        browse_btn.setText("…")
        browse_btn.setToolTip("Browse for folder")
        browse_btn.clicked.connect(self._browse)

        self._module_edit = QtWidgets.QLineEdit(module)
        self._module_edit.setPlaceholderText("module name")
        self._module_edit.setFixedWidth(130)

        remove_btn = QtWidgets.QToolButton()
        remove_btn.setText("✕")
        remove_btn.setToolTip("Remove this plugin")
        remove_btn.clicked.connect(self.remove_requested)

        layout.addWidget(self._path_edit, stretch=1)
        layout.addWidget(browse_btn)
        layout.addWidget(self._module_edit)
        layout.addWidget(remove_btn)

    def _browse(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select plugin src/ folder", self._path_edit.text()
        )
        if folder:
            self._path_edit.setText(folder)

    def get_value(self) -> dict:
        return {
            "path":   self._path_edit.text().strip(),
            "module": self._module_edit.text().strip(),
        }


class PluginListWidget(QtWidgets.QWidget):
    """Full-width widget that manages a list of path-plugin entries."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(4)

        # column headers
        header = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(8, 0, 8, 0)
        h_layout.setSpacing(6)
        lbl_path = QtWidgets.QLabel("Path (src/ folder)")
        lbl_path.setObjectName("pref_row_desc")
        lbl_mod  = QtWidgets.QLabel("Module name")
        lbl_mod.setObjectName("pref_row_desc")
        lbl_mod.setFixedWidth(130)
        h_layout.addWidget(lbl_path, stretch=1)
        h_layout.addSpacing(24)   # browse btn width
        h_layout.addWidget(lbl_mod)
        h_layout.addSpacing(24)   # remove btn width
        root.addWidget(header)

        self._rows_container = QtWidgets.QWidget()
        self._rows_layout    = QtWidgets.QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(2)
        root.addWidget(self._rows_container)

        add_btn = QtWidgets.QPushButton("+ Add plugin")
        add_btn.setFixedWidth(120)
        add_btn.clicked.connect(lambda: self._add_row())
        root.addWidget(add_btn, alignment=QtCore.Qt.AlignmentFlag.AlignLeft
                       if hasattr(QtCore.Qt, "AlignmentFlag")
                       else QtCore.Qt.AlignLeft)

        self._rows: list[_PluginRow] = []

    def _add_row(self, path: str = "", module: str = "") -> None:
        row = _PluginRow(path, module, self._rows_container)
        row.remove_requested.connect(lambda r=row: self._remove_row(r))
        self._rows_layout.addWidget(row)
        self._rows.append(row)

    def _remove_row(self, row: _PluginRow) -> None:
        self._rows_layout.removeWidget(row)
        self._rows.remove(row)
        row.deleteLater()

    # ── PreferencesPanel interface ──────────────────────────────────────

    def get_value(self) -> list[dict]:
        return [r.get_value() for r in self._rows
                if r.get_value()["path"] or r.get_value()["module"]]

    def set_value(self, entries: list[dict]) -> None:
        for row in list(self._rows):
            self._remove_row(row)
        for entry in (entries or []):
            self._add_row(entry.get("path", ""), entry.get("module", ""))
