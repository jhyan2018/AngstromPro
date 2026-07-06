# -*- coding: utf-8 -*-
"""
Created on 2026-07-06

@author: jiahaoYan

Dialog for reviewing and renaming curves before extracting them to the workspace.
"""
from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets


class ExtractCurvesDialog(QtWidgets.QDialog):
    """
    Shows a list of curves about to be extracted with editable name fields.
    User can rename each item before confirming.
    """

    def __init__(self, pairs: list[tuple[str, object]],
                 parent=None) -> None:
        super().__init__(parent)
        self._pairs = pairs          # [(suggested_name, UdsDataStru)]
        self._editors: list[QtWidgets.QLineEdit] = []
        self.setWindowTitle("Extract Curves to Workspace")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel(
            "Each selected curve will become a new WorkspaceItem.\n"
            "Edit names below before extracting:"))

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        form  = QtWidgets.QFormLayout(inner)
        form.setContentsMargins(4, 4, 4, 4)

        for i, (name, _uds) in enumerate(self._pairs):
            ed = QtWidgets.QLineEdit(name)
            form.addRow(f"Curve {i + 1}:", ed)
            self._editors.append(ed)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def result_pairs(self) -> list[tuple[str, object]]:
        """Return (final_name, UdsDataStru) pairs after user editing."""
        result = []
        for ed, (_orig_name, uds) in zip(self._editors, self._pairs):
            name = ed.text().strip() or _orig_name
            uds.name = name
            result.append((name, uds))
        return result
