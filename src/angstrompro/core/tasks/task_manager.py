"""
TaskManager — unified entry point for all background task execution.

Wraps ThreadPoolExecutor, WorkerThreadExecutor, and TaskDispatcher.
Tracks all active handles and supports bulk cancellation.

Usage
-----
    manager = TaskManager(max_pool_threads=4)

    handle = manager.submit(TaskRequest(
        task_id   = "crop_001",
        task_func = my_func,
        backend   = "auto",          # "auto" | "pool" | "worker"
    ))
    handle.result.connect(my_result_slot)
    handle.error.connect(my_error_slot)

    manager.cancel("crop_001")
    manager.cancel_all()
"""

import logging

from angstrompro.utils.qt_compat import QtCore

from .pool_executor import ThreadPoolExecutor
from .worker_executor import WorkerThreadExecutor
from .task_dispatcher import TaskDispatcher
from .task_handle import TaskHandle
from .task_request import TaskRequest

log = logging.getLogger(__name__)


class TaskManager(QtCore.QObject):
    def __init__(
        self,
        max_pool_threads: int = 4,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pool_executor   = ThreadPoolExecutor(max_pool_threads, parent=self)
        self._worker_executor = WorkerThreadExecutor(parent=self)
        self._dispatcher      = TaskDispatcher(
            self._pool_executor, self._worker_executor, parent=self
        )
        self._handles: dict[str, TaskHandle] = {}

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit(self, request: TaskRequest) -> TaskHandle:
        if request.task_id in self._handles:
            raise ValueError(
                f"Task {request.task_id!r} is already running. "
                f"Use a unique task_id or cancel the existing task first."
            )
        handle = self._dispatcher.submit(request)
        self._handles[request.task_id] = handle
        handle.result.connect(lambda r, t=request.task_id: self._on_done(t))
        handle.error.connect( lambda e, t=request.task_id: self._on_done(t))
        log.debug("Task submitted: %s  backend=%s", request.task_id, request.backend)
        return handle

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def is_running(self, task_id: str) -> bool:
        return task_id in self._handles

    def active_task_ids(self) -> list[str]:
        return list(self._handles.keys())

    def active_count(self) -> int:
        return len(self._handles)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_done(self, task_id: str) -> None:
        self._handles.pop(task_id, None)
        log.debug("Task done: %s", task_id)
