# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 2026

@author: jiahaoYan

TaskDashboard — live view of all tasks submitted through TaskManager.

Observes context.tasks.task_submitted and automatically tracks every task,
regardless of which module submitted it. No tasks are created here.
"""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QT_API
from angstrompro.app.context import AppContext


class DemoWindow(QtWidgets.QWidget):
    """Task Dashboard — passive observer of all TaskManager activity."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.setWindowTitle(f"Task Dashboard ({QT_API})")
        self.resize(900, 400)

        self._manager  = context.tasks
        self._handles:     dict[str, object] = {}   # task_id → TaskHandle
        self._cancellable: dict[str, bool]   = {}   # task_id → bool

        self._setup_ui()

        # Connect to TaskManager's global submission signal
        self._manager.task_submitted.connect(self._on_task_submitted)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # status + cancel row
        top_row = QtWidgets.QHBoxLayout()
        self._status_label = QtWidgets.QLabel("No tasks yet.")
        top_row.addWidget(self._status_label)
        top_row.addStretch()
        self._btn_cancel = QtWidgets.QPushButton("Cancel Selected")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel_selected)
        top_row.addWidget(self._btn_cancel)
        layout.addLayout(top_row)

        # task tree
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(6)
        self._tree.setHeaderLabels(
            ["Task ID", "Source", "Type", "Backend", "State", "Progress"])
        self._tree.header().setStretchLastSection(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._tree)

        # log
        layout.addWidget(QtWidgets.QLabel("Log:"))
        self._log_box = QtWidgets.QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setMaximumHeight(120)
        layout.addWidget(self._log_box)

    # ------------------------------------------------------------------
    # Task observation
    # ------------------------------------------------------------------

    def _on_task_submitted(self, request, handle) -> None:
        """Called for every task submitted anywhere in the app."""
        self._handles[handle.task_id]     = handle
        self._cancellable[handle.task_id] = request.cancellable

        # Add row
        item = QtWidgets.QTreeWidgetItem([
            request.task_id[:8],
            request.source_id or "—",
            request.task_type or "—",
            request.backend,
            "Pending",
            "",
        ])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, handle.task_id)
        self._tree.addTopLevelItem(item)
        self._tree.scrollToItem(item)

        Q = QtCore.Qt.ConnectionType.QueuedConnection
        handle.started.connect(
            lambda tid=handle.task_id: self._on_started(tid), Q)
        handle.progress.connect(
            lambda tid, cur, tot: self._on_progress(tid, cur, tot), Q)
        handle.result.connect(
            lambda tid, res: self._on_result(tid, res), Q)
        handle.error.connect(
            lambda tid, err: self._on_error(tid, err), Q)
        handle.cancelled.connect(
            lambda tid=handle.task_id: self._on_cancelled(tid), Q)

        self._log(f"[{request.task_type}] {request.source_id} "
                  f"({handle.task_id[:8]}) submitted")
        self._update_status()

    # ------------------------------------------------------------------
    # Handle signals
    # ------------------------------------------------------------------

    def _on_started(self, task_id: str) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Running")
        self._log(f"({task_id[:8]}) started")
        self._update_status()

    def _on_progress(self, task_id: str, current: int, total: int) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(5, f"{current}/{total}")

    def _on_result(self, task_id: str, _result) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Done")
            item.setText(5, "")
        self._log(f"({task_id[:8]}) done")
        self._finish(task_id)

    def _on_error(self, task_id: str, error_text: str) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Error")
            item.setText(5, "")
        self._log(f"({task_id[:8]}) ERROR: {error_text.splitlines()[0]}")
        self._finish(task_id)

    def _on_cancelled(self, task_id: str) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Cancelled")
            item.setText(5, "")
        self._log(f"({task_id[:8]}) cancelled")
        self._finish(task_id)

    def _finish(self, task_id: str) -> None:
        self._handles.pop(task_id, None)
        self._cancellable.pop(task_id, None)
        self._on_selection_changed(self._tree.currentItem(), None)
        self._update_status()

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def _cancel_selected(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        task_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        handle  = self._handles.get(task_id)
        if handle:
            handle.cancel()
            item.setText(4, "Cancelling")
            self._btn_cancel.setEnabled(False)
            self._log(f"({task_id[:8]}) cancel requested")

    def _on_selection_changed(self, current, _previous) -> None:
        if current is None:
            self._btn_cancel.setEnabled(False)
            return
        task_id       = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        is_running    = task_id in self._handles
        is_cancelable = self._cancellable.get(task_id, False)
        self._btn_cancel.setEnabled(is_running and is_cancelable)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _item_for(self, task_id: str) -> QtWidgets.QTreeWidgetItem | None:
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.data(0, QtCore.Qt.ItemDataRole.UserRole) == task_id:
                return item
        return None

    def _log(self, text: str) -> None:
        self._log_box.append(text)

    def _update_status(self) -> None:
        n = len(self._handles)
        self._status_label.setText(
            f"{n} task{'s' if n != 1 else ''} running"
            if n else "All tasks complete."
        )
