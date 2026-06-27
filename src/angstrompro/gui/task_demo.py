import sys
import time

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QT_API
from angstrompro.core.tasks import TaskRequest
from angstrompro.app.context import AppContext


# =========================================================
# Demo task functions
# =========================================================
def demo_compute_task(n=10, sleep_s=0.15):
    result = []
    for i in range(n):
        time.sleep(sleep_s)
        result.append(i * i)
    return f"Compute result: {result}"


def demo_io_task(n=8, sleep_s=0.25, cancel_token=None, progress_callback=None):
    total = 0
    for i in range(n):
        if cancel_token is not None and cancel_token.is_cancelled():
            return "io task cancelled"
        time.sleep(sleep_s)
        total += (i + 1) * 10
        if progress_callback is not None:
            progress_callback(i + 1, n)
    return f"IO result: total={total}"


def demo_worker_task(n=6, sleep_s=0.4, cancel_token=None, progress_callback=None):
    results = []
    for i in range(n):
        if cancel_token is not None and cancel_token.is_cancelled():
            return "worker task cancelled"
        time.sleep(sleep_s)
        results.append(f"step_{i}")
        if progress_callback is not None:
            progress_callback(i + 1, n)
    return f"Worker result: {results}"


# =========================================================
# Demo window
# =========================================================
class DemoWindow(QtWidgets.QWidget):
    def __init__(self, context: AppContext):
        super().__init__()
        self.setWindowTitle(f"TaskManager Demo ({QT_API})")
        self.resize(1000, 600)

        self.manager = context.tasks

        self.handles        = {}
        self.cancellable    = {}   # task_id → bool
        self.compute_counter = 0
        self.io_counter      = 0

        self.status_label    = QtWidgets.QLabel("Idle")
        self.btn_add_compute = QtWidgets.QPushButton("Add Compute Task")
        self.btn_add_io      = QtWidgets.QPushButton("Add IO Task (cancellable + progress)")
        self.btn_add_worker  = QtWidgets.QPushButton("Add Worker Task (cancellable + progress)")
        self.btn_cancel      = QtWidgets.QPushButton("Cancel Selected")

        self.task_tree = QtWidgets.QTreeWidget()
        self.task_tree.setColumnCount(6)
        self.task_tree.setHeaderLabels(["Task ID", "Source", "Type", "Backend", "State", "Progress"])

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.btn_add_compute)
        row.addWidget(self.btn_add_io)
        row.addWidget(self.btn_add_worker)
        row.addWidget(self.btn_cancel)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addLayout(row)
        layout.addWidget(QtWidgets.QLabel("Task Records:"))
        layout.addWidget(self.task_tree)
        layout.addWidget(QtWidgets.QLabel("Log:"))
        layout.addWidget(self.log_box)
        self.setLayout(layout)

        self.btn_add_compute.clicked.connect(self.add_compute_task)
        self.btn_add_io.clicked.connect(self.add_io_task)
        self.btn_add_worker.clicked.connect(self.add_worker_task)
        self.btn_cancel.clicked.connect(self.cancel_selected)
        self.task_tree.currentItemChanged.connect(self._on_selection_changed)
        self.btn_cancel.setEnabled(False)

    def log(self, text: str) -> None:
        self.log_box.append(text)

    def add_tree_item(self, request: TaskRequest) -> None:
        item = QtWidgets.QTreeWidgetItem([
            request.task_id[:8],
            request.source_id,
            request.task_type,
            request.backend,
            "Pending",
            "",
        ])
        self.task_tree.addTopLevelItem(item)
        # store full task_id in UserRole for lookup
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, request.task_id)

    def _item_for(self, task_id: str) -> QtWidgets.QTreeWidgetItem | None:
        for i in range(self.task_tree.topLevelItemCount()):
            item = self.task_tree.topLevelItem(i)
            if item.data(0, QtCore.Qt.ItemDataRole.UserRole) == task_id:
                return item
        return None

    def connect_handle(self, handle, request: TaskRequest) -> None:
        self.handles[handle.task_id]     = handle
        self.cancellable[handle.task_id] = request.cancellable
        self.add_tree_item(request)
        Q = QtCore.Qt.ConnectionType.QueuedConnection
        handle.started.connect(self.on_started, Q)
        handle.progress.connect(self.on_progress, Q)
        handle.result.connect(self.on_result, Q)
        handle.error.connect(self.on_error, Q)
        handle.cancelled.connect(self.on_cancelled, Q)

    def add_compute_task(self) -> None:
        self.compute_counter += 1
        request = TaskRequest(
            task_func=demo_compute_task,
            source_id="task_demo",
            task_type="demo_compute",
            kwargs={"n": 60, "sleep_s": 0.3},
            backend="compute",
            priority="normal",
        )
        handle = self.manager.submit(request)
        self.connect_handle(handle, request)
        self.log(f"[{request.task_type}] {request.source_id} ({handle.task_id[:8]}) submitted")

    def add_io_task(self) -> None:
        self.io_counter += 1
        request = TaskRequest(
            task_func=demo_io_task,
            source_id="task_demo",
            task_type="demo_io",
            kwargs={"n": 80, "sleep_s": 0.3},
            backend="io",
            cancellable=True,
            has_progress=True,
            priority="normal",
            timeout_s=30.0,
        )
        handle = self.manager.submit(request)
        self.connect_handle(handle, request)
        self.log(f"[{request.task_type}] {request.source_id} ({handle.task_id[:8]}) submitted")

    def add_worker_task(self) -> None:
        request = TaskRequest(
            task_func=demo_worker_task,
            source_id="task_demo",
            task_type="demo_worker",
            kwargs={"n": 60, "sleep_s": 0.4},
            backend="worker",
            cancellable=True,
            has_progress=True,
            priority="normal",
            timeout_s=60.0,
        )
        handle = self.manager.submit(request)
        self.connect_handle(handle, request)
        self.log(f"[{request.task_type}] {request.source_id} ({handle.task_id[:8]}) submitted")

    def _on_selection_changed(self, current, previous) -> None:
        if current is None:
            self.btn_cancel.setEnabled(False)
            return
        task_id = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        is_running     = task_id in self.handles
        is_cancellable = self.cancellable.get(task_id, False)
        self.btn_cancel.setEnabled(is_running and is_cancellable)

    def cancel_selected(self) -> None:
        item = self.task_tree.currentItem()
        if item is None:
            self.log("[GUI] no task selected")
            return
        task_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        handle = self.handles.get(task_id)
        if handle is not None:
            handle.cancel()
            item.setText(4, "Cancelling")
            self.btn_cancel.setEnabled(False)
            self.log(f"({task_id[:8]}) cancel requested")

    def on_started(self, task_id) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Running")
        self.status_label.setText(f"({task_id[:8]}): running")
        self.log(f"({task_id[:8]}) started")

    def on_progress(self, task_id, current, total) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(5, f"{current}/{total}")

    def on_result(self, task_id, result_obj) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Done")
            item.setText(5, "")
        self.status_label.setText(f"({task_id[:8]}): done")
        self.log(f"({task_id[:8]}) result: {result_obj}")
        self.handles.pop(task_id, None)
        self.cancellable.pop(task_id, None)
        self._on_selection_changed(self.task_tree.currentItem(), None)

    def on_cancelled(self, task_id) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Cancelled")
            item.setText(5, "")
        self.status_label.setText(f"({task_id[:8]}): cancelled")
        self.log(f"({task_id[:8]}) cancelled")
        self.handles.pop(task_id, None)
        self.cancellable.pop(task_id, None)
        self._on_selection_changed(self.task_tree.currentItem(), None)

    def on_error(self, task_id, error_text) -> None:
        item = self._item_for(task_id)
        if item:
            item.setText(4, "Error")
        self.status_label.setText(f"({task_id[:8]}): error")
        self.log(f"({task_id[:8]}) ERROR:\n{error_text}")
        self.handles.pop(task_id, None)
        self.cancellable.pop(task_id, None)
        self._on_selection_changed(self.task_tree.currentItem(), None)

