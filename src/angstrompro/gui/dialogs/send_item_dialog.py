# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 2026

@author: jiahaoYan

SendItemDialog — select a target module to send a workspace item to.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtWidgets

if TYPE_CHECKING:
    from angstrompro.core.modules.module_mixin import ModuleMixin
    from angstrompro.app.context import AppContext


class SendItemDialog(QtWidgets.QDialog):

    def __init__(self, context: "AppContext", exclude_instance_id: str,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Send Item To…")
        self.resize(300, 300)
        self._context = context
        self._exclude = exclude_instance_id
        self._selected: "ModuleMixin | None" = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Select target module:"))

        self._list = QtWidgets.QListWidget()
        self._list.itemDoubleClicked.connect(self._accept)
        layout.addWidget(self._list)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        self._list.clear()
        self._instances = [
            inst for inst in self._context.module_manager.list_instances()
            if inst.instance_id != self._exclude
        ]
        for inst in self._instances:
            label = f"{inst.display_name or inst.module_id}  [{inst.instance_id}]"
            self._list.addItem(label)

    def _accept(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        self._selected = self._instances[row]
        self.accept()

    @property
    def selected_module(self) -> "ModuleMixin | None":
        return self._selected
