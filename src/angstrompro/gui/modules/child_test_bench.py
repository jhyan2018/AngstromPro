# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 13:20:46 2026

@author: jiahaoYan
"""

from __future__ import annotations
import time
import numpy as np
from angstrompro.app.context import AppContext
from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.modules.a_gui_module import AGuiModule
from angstrompro.core.modules.a_module_manager import register_module
from angstrompro.core.tasks.task_request import TaskRequest
from angstrompro.core.workspaces.workspace_item import WorkspaceItem
from angstrompro.utils.qt_compat import QtCore, QtWidgets


def _fake_long_task(cancel_token=None, progress_callback=None):
    """60-step fake task (~1 min). Supports cancellation and progress reporting."""
    steps = 60
    for i in range(steps):
        if cancel_token is not None and cancel_token.is_cancelled():
            return "cancelled"
        time.sleep(1)
        if progress_callback is not None:
            progress_callback(i + 1, steps)
    return "fake task complete"


@register_module
class ChildTestBench(AGuiModule):
    module_id            = "test_bench"
    display_name         = "Test Bench"
    category             = "Basic"
    default_process_menu = ["spatial.crop2d"]

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self._counter = 0
        self.resize(700, 480)
        self.setWindowTitle(f"Test Bench — {self.instance_id}")

    # ------------------------------------------------------------------
    # AGuiModule contract
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout  = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # --- process_inputs monitor ---
        layout.addWidget(QtWidgets.QLabel("process_inputs (staged for next process):"))
        self._inputs_list = QtWidgets.QListWidget()
        self._inputs_list.setMaximumHeight(110)
        self._inputs_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self._inputs_list)

        # --- buttons row ---
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_add_aux = QtWidgets.QPushButton("Add to aux (append to process_inputs)")
        self._btn_add_aux.setToolTip(
            "Append the currently selected workspace item as the second process input.")
        self._btn_add_aux.clicked.connect(self._on_add_aux)
        btn_row.addWidget(self._btn_add_aux)

        self._btn_fake_task = QtWidgets.QPushButton("Run Fake Long Task (60 s, with progress)")
        self._btn_fake_task.clicked.connect(self._on_run_fake_task)
        btn_row.addWidget(self._btn_fake_task)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        self.setCentralWidget(central)

    def on_item_loaded(self, item: WorkspaceItem) -> None:
        """Double-click in workspace: clear process_inputs and stage this item as primary."""
        self.process_inputs = [item]
        self._refresh_inputs_list()

    def on_add_item(self) -> None:
        self._counter += 1
        ndim = (self._counter % 3) + 1          # cycles 1D → 2D → 3D for easy testing
        shape = {1: (20,), 2: (8, 10), 3: (4, 5, 6)}[ndim]
        name    = f"{self.instance_id}_item{self._counter}_{ndim}D"
        payload = UdsDataStru.from_array(np.random.rand(*shape), name)
        self.workspace.add_item(name=name, payload=payload)

    # ------------------------------------------------------------------
    # "Add to aux" — append selected item as second process input
    # ------------------------------------------------------------------

    def _on_add_aux(self) -> None:
        name = self._selected_item_name()
        if name is None:
            QtWidgets.QMessageBox.information(
                self, "No selection", "Select a workspace item first.")
            return
        item = self.workspace.get_item(name)
        # Avoid duplicates: replace if already present, otherwise append
        existing_names = [i.name for i in self.process_inputs]
        if item.name in existing_names:
            QtWidgets.QMessageBox.information(
                self, "Already staged",
                f"'{item.name}' is already in process_inputs.")
            return
        self.process_inputs.append(item)
        self._refresh_inputs_list()

    # ------------------------------------------------------------------
    # process_inputs display
    # ------------------------------------------------------------------

    def _refresh_inputs_list(self) -> None:
        self._inputs_list.clear()
        if not self.process_inputs:
            placeholder = QtWidgets.QListWidgetItem("(empty)")
            placeholder.setForeground(
                QtWidgets.QApplication.palette().color(
                    QtWidgets.QPalette.ColorRole.Mid
                    if hasattr(QtWidgets.QPalette.ColorRole, "Mid")
                    else QtWidgets.QPalette.Mid
                )
            )
            self._inputs_list.addItem(placeholder)
            return
        for i, item in enumerate(self.process_inputs):
            ndim = getattr(getattr(item.payload, "data", None), "ndim", "?")
            shape = getattr(getattr(item.payload, "data", None), "shape", "?")
            label = f"[{i}]  {item.name}  type={item.type_id}  ndim={ndim}  shape={shape}"
            self._inputs_list.addItem(label)

    # ------------------------------------------------------------------
    # Fake long task — tests progress reporting and status bar
    # ------------------------------------------------------------------

    def _on_run_fake_task(self) -> None:
        request = TaskRequest(
            task_func    = _fake_long_task,
            source_id    = self.instance_id,
            task_type    = "fake_long_task",
            backend      = "compute",
            cancellable  = True,
            has_progress = True,
        )
        handle = self._context.tasks.submit(request)

        sb = self.statusBar()
        sb.showMessage("Fake task: running…")
        handle.progress.connect(
            lambda _tid, cur, tot: sb.showMessage(f"Fake task: {cur}/{tot}"))
        handle.result.connect(
            lambda _tid, _res: sb.showMessage("Fake task: done.", 5000))
        handle.error.connect(
            lambda _tid, _err: sb.showMessage("Fake task: failed.", 8000))
        handle.cancelled.connect(
            lambda _tid: sb.showMessage("Fake task: cancelled.", 5000))
