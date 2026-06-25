# -*- coding: utf-8 -*-
"""
SetDefaultTargetsDialog — pick one or more default send-target modules.

Opened when the user checks "Default" in the workspace dock Send row.
Multi-select list of all live modules except the caller.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from angstrompro.utils.qt_compat import QtWidgets

if TYPE_CHECKING:
    from angstrompro.core.modules.module_mixin import ModuleMixin
    from angstrompro.app.context import AppContext


class SetDefaultTargetsDialog(QtWidgets.QDialog):

    def __init__(self, context: "AppContext", exclude_instance_id: str,
                 current_target_ids: list[str] | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Default Send Targets…")
        self.resize(320, 320)
        self._context = context
        self._exclude = exclude_instance_id
        self._current = set(current_target_ids or [])
        self._selected: list["ModuleMixin"] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Select default target module(s):"))

        self._list = QtWidgets.QListWidget()
        self._list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
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
            item = QtWidgets.QListWidgetItem(label)
            self._list.addItem(item)
            if inst.instance_id in self._current:
                item.setSelected(True)

    def _accept(self) -> None:
        self._selected = [
            self._instances[self._list.row(item)]
            for item in self._list.selectedItems()
        ]
        self.accept()

    @property
    def selected_modules(self) -> list["ModuleMixin"]:
        return self._selected
