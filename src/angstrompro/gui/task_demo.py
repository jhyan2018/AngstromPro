import sys
import time

from angstrompro.utils.qt_compat import QtCore, QtWidgets, QT_API, exec_app, run_qt_app
from angstrompro.core.tasks import (
    TaskRequest, TaskDispatcher,
    ThreadPoolExecutor, WorkerThreadExecutor,
)


# =========================================================
# Demo task functions
# =========================================================
def demo_pool_task(ctx, n=10, sleep_s=0.15):
    result = []
    for i in range(n):
        if ctx.is_cancelled():
            return "pool task cancelled"
        time.sleep(sleep_s)
        result.append(i * i)
        ctx.set_progress((i + 1) / n * 100, f"Pool step {i + 1}/{n}")
    return f"Pool result: {result}"


def demo_worker_task(ctx, n=8, sleep_s=0.25):
    total = 0
    for i in range(n):
        if ctx.is_cancelled():
            return "worker task cancelled"
        time.sleep(sleep_s)
        total += (i + 1) * 10
        ctx.set_progress((i + 1) / n * 100, f"Worker step {i + 1}/{n}")
    return f"Worker result: total={total}"


# =========================================================
# Demo window
# =========================================================
class DemoWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Multi-Task Dispatcher Demo ({QT_API})")
        self.resize(950, 600)

        self.pool_executor   = ThreadPoolExecutor(max_thread_count=3, parent=self)
        self.worker_executor = WorkerThreadExecutor(parent=self)
        self.dispatcher      = TaskDispatcher(
            pool_executor=self.pool_executor,
            worker_executor=self.worker_executor,
            parent=self,
        )

        self.handles        = {}
        self.task_items     = {}
        self.pool_counter   = 0
        self.worker_counter = 0

        self.status_label        = QtWidgets.QLabel("Idle")
        self.btn_add_pool        = QtWidgets.QPushButton("Add Pool Task")
        self.btn_add_worker      = QtWidgets.QPushButton("Add Worker Task")
        self.btn_cancel_selected = QtWidgets.QPushButton("Cancel Selected Task")

        self.task_tree = QtWidgets.QTreeWidget()
        self.task_tree.setColumnCount(5)
        self.task_tree.setHeaderLabels(["Task ID", "Backend", "Progress", "State", "Message"])

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.btn_add_pool)
        row.addWidget(self.btn_add_worker)
        row.addWidget(self.btn_cancel_selected)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addLayout(row)
        layout.addWidget(QtWidgets.QLabel("Task Records:"))
        layout.addWidget(self.task_tree)
        layout.addWidget(QtWidgets.QLabel("Log:"))
        layout.addWidget(self.log_box)
        self.setLayout(layout)

        self.btn_add_pool.clicked.connect(self.add_pool_task)
        self.btn_add_worker.clicked.connect(self.add_worker_task)
        self.btn_cancel_selected.clicked.connect(self.cancel_selected_task)

    def log(self, text: str) -> None:
        self.log_box.append(text)

    def add_task_item(self, task_id: str, backend: str) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([task_id, backend, "0%", "Submitted", ""])
        self.task_tree.addTopLevelItem(item)
        self.task_items[task_id] = item
        return item

    def update_task_item(self, task_id, progress=None, state=None, message=None) -> None:
        item = self.task_items.get(task_id)
        if item is None:
            return
        if progress is not None:
            item.setText(2, f"{int(progress)}%")
        if state is not None:
            item.setText(3, state)
        if message is not None:
            item.setText(4, message)

    def connect_handle(self, handle, backend: str) -> None:
        self.handles[handle.task_id] = handle
        self.add_task_item(handle.task_id, backend)
        handle.progress.connect(self.on_task_progress)
        handle.result.connect(self.on_task_result)
        handle.error.connect(self.on_task_error)
        handle.finished.connect(self.on_task_finished)

    def add_pool_task(self) -> None:
        self.pool_counter += 1
        task_id = f"pool_task_{self.pool_counter}"
        request = TaskRequest(
            task_id=task_id,
            task_func=demo_pool_task,
            kwargs={"n": 80 + self.pool_counter, "sleep_s": 0.5},
            backend="pool",
        )
        handle = self.dispatcher.submit(request)
        self.connect_handle(handle, "pool")
        self.log(f"[{task_id}] submitted to ThreadPoolExecutor")

    def add_worker_task(self) -> None:
        self.worker_counter += 1
        task_id = f"worker_task_{self.worker_counter}"
        request = TaskRequest(
            task_id=task_id,
            task_func=demo_worker_task,
            kwargs={"n": 100 + self.worker_counter, "sleep_s": 0.5},
            backend="worker",
            metadata={"needs_dedicated_thread": True},
        )
        handle = self.dispatcher.submit(request)
        self.connect_handle(handle, "worker")
        self.log(f"[{task_id}] submitted to WorkerThreadExecutor")

    def cancel_selected_task(self) -> None:
        item = self.task_tree.currentItem()
        if item is None:
            self.log("[GUI] no task selected")
            return
        task_id = item.text(0)
        handle = self.handles.get(task_id)
        if handle is not None:
            handle.cancel()
            self.update_task_item(task_id, state="Cancelling")
            self.log(f"[{task_id}] cancel requested")

    def on_task_progress(self, task_id, percent, message) -> None:
        self.status_label.setText(f"{task_id}: {percent}% - {message}")
        self.update_task_item(task_id, progress=percent, state="Running", message=message)
        self.log(f"[{task_id}] {percent}% - {message}")

    def on_task_result(self, task_id, result_obj) -> None:
        self.update_task_item(task_id, state="Result", message=str(result_obj))
        self.log(f"[{task_id}] result received: {result_obj}")

    def on_task_error(self, task_id, error_text) -> None:
        self.update_task_item(task_id, state="Error", message="See log")
        self.log(f"[{task_id}] ERROR:\n{error_text}")

    def on_task_finished(self, task_id) -> None:
        item = self.task_items.get(task_id)
        current_state = item.text(3) if item is not None else ""
        if current_state == "Cancelling":
            self.update_task_item(task_id, state="Finished", message="Cancelled or exited")
        elif current_state not in ("Error", "Result"):
            self.update_task_item(task_id, state="Finished")
        self.status_label.setText(f"{task_id} finished")
        self.log(f"[{task_id}] finished")
        self.handles.pop(task_id, None)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    sys.exit(run_qt_app(app))
