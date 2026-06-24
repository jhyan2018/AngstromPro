# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 13:20:46 2026

@author: jiahaoYan
"""

from __future__ import annotations
import numpy as np
from angstrompro.utils.qt_compat import QtWidgets
from angstrompro.app.context import AppContext
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.workspaces.workspace_item import WorkspaceItem


@register_module
class ChildTestBench(AGuiModule):
    module_id    = "child_bench"
    display_name = "Child Bench"

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self._counter = 0
        self.resize(600, 400)
        self.setWindowTitle(f"Child Bench — {self.instance_id}")

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        central = QtWidgets.QWidget()
        central.setLayout(layout)

        self._list = QtWidgets.QListWidget()
        layout.addWidget(self._list)

        btn_add = QtWidgets.QPushButton("Add Item")
        btn_add.clicked.connect(self._add_item)
        layout.addWidget(btn_add)

        btn_remove = QtWidgets.QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._remove_item)
        layout.addWidget(btn_remove)

        btn_send = QtWidgets.QPushButton("Send Selected to Main")
        btn_send.clicked.connect(self._send_item)
        layout.addWidget(btn_send)

        self.setCentralWidget(central)

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        pass

    def on_workspace_changed(self) -> None:
        self._refresh_list()

    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        self._list.clear()
        for name in self.workspace.list_names():
            self._list.addItem(name)

    def _selected_name(self) -> str | None:
        item = self._list.currentItem()
        return item.text() if item else None

    def _add_item(self) -> None:
        self._counter += 1
        name = f"{self.instance_id}_item_{self._counter}"
        payload = UdsDataStru.from_array(np.zeros(10), name)
        self.workspace.add_item(name=name, payload=payload)

    def _remove_item(self) -> None:
        name = self._selected_name()
        if name:
            self.workspace.remove_item(name)

    def _send_item(self) -> None:
        name = self._selected_name()
        if not name:
            return
        targets = self._context.module_manager.list_instances("main_workbench")
        if not targets:
            return
        self._context.workspace_manager.transfer_item(
            src_workspace_id=self.workspace.workspace_id,
            dst_workspace_id=targets[0].workspace.workspace_id,
            item_name=name,
        )
        print(f"[{self.instance_id}] sent '{name}' to main")
