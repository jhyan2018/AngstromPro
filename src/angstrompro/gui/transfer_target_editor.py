# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 14:07:07 2026

@author: jiahaoYan
"""

# angstrompro/gui/transfer_target_editor.py
from __future__ import annotations
from angstrompro.utils.qt_compat import QtWidgets
from angstrompro.app.context import AppContext


class TransferTargetEditor(QtWidgets.QDialog):
    """
    Edit transfer targets for each module.
    """

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self._targets: dict[str, list[str]] = {}
        self.setWindowTitle("Transfer Target Editor")
        self.resize(600, 400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QHBoxLayout(self)

        # --- left: module list ---
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.addWidget(QtWidgets.QLabel("Modules:"))
        self._module_list = QtWidgets.QListWidget()
        self._module_list.currentItemChanged.connect(self._on_module_selected)
        left_layout.addWidget(self._module_list)
        layout.addWidget(left)

        # --- right: target management ---
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        right_layout.addWidget(QtWidgets.QLabel("Current Targets:"))
        self._target_list = QtWidgets.QListWidget()
        right_layout.addWidget(self._target_list)

        btn_add = QtWidgets.QPushButton("Add Target")
        btn_add.clicked.connect(self._add_target)
        right_layout.addWidget(btn_add)

        btn_remove = QtWidgets.QPushButton("Remove Selected Target")
        btn_remove.clicked.connect(self._remove_target)
        right_layout.addWidget(btn_remove)

        layout.addWidget(right)

        self._refresh_module_list()

    def _live_workspaces(self) -> list:
        return self.context.workspace_manager.list_workspaces()

    def _ws_label(self, ws) -> str:
        return f"{ws.label or ws.owner_id}  [{ws.workspace_id[:8]}]"

    def _refresh_module_list(self) -> None:
        self._module_list.clear()
        for ws in self._live_workspaces():
            item = QtWidgets.QListWidgetItem(self._ws_label(ws))
            item.setData(QtWidgets.QListWidgetItem.ItemType.Type, ws.workspace_id)
            self._module_list.addItem(item)

    def _refresh_target_list(self) -> None:
        self._target_list.clear()
        ws_id = self._selected_ws_id()
        if not ws_id:
            return
        for target_ws_id in self._targets.get(ws_id, []):
            try:
                ws = self.context.workspace_manager.get_workspace(target_ws_id)
                label = self._ws_label(ws)
            except KeyError:
                label = target_ws_id
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtWidgets.QListWidgetItem.ItemType.Type, target_ws_id)
            self._target_list.addItem(item)

    def _selected_ws_id(self) -> str | None:
        item = self._module_list.currentItem()
        return item.data(QtWidgets.QListWidgetItem.ItemType.Type) if item else None

    def _selected_target_ws_id(self) -> str | None:
        item = self._target_list.currentItem()
        return item.data(QtWidgets.QListWidgetItem.ItemType.Type) if item else None

    def _on_module_selected(self) -> None:
        self._refresh_target_list()

    def _add_target(self) -> None:
        ws_id = self._selected_ws_id()
        if not ws_id:
            return

        current_targets = self._targets.get(ws_id, [])
        available = [ws for ws in self._live_workspaces()
                     if ws.workspace_id != ws_id and ws.workspace_id not in current_targets]

        if not available:
            QtWidgets.QMessageBox.information(self, "No candidates", "No other workspaces available.")
            return

        labels = [self._ws_label(ws) for ws in available]
        label, ok = QtWidgets.QInputDialog.getItem(
            self, "Add Target", "Select workspace to add as target:", labels, editable=False
        )
        if ok and label:
            chosen = available[labels.index(label)]
            self._targets.setdefault(ws_id, []).append(chosen.workspace_id)
            self._refresh_target_list()

    def _remove_target(self) -> None:
        ws_id = self._selected_ws_id()
        target_ws_id = self._selected_target_ws_id()
        if not ws_id or not target_ws_id:
            return
        targets = self._targets.get(ws_id, [])
        if target_ws_id in targets:
            targets.remove(target_ws_id)
        self._refresh_target_list()