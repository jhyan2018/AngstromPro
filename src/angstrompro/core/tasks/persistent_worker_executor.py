# -*- coding: utf-8 -*-
"""
Created on Tue Jul 15 2026

@author: jiahaoYan
"""
import logging
import traceback

from angstrompro.utils.qt_compat import QtCore, Signal, Slot

from .task_request import TaskRequest
from .pool_executor import _RunSignals

log = logging.getLogger(__name__)


class _PersistentWorker(QtCore.QObject):
    started   = Signal()
    result    = Signal(object)
    error     = Signal(str)
    cancelled = Signal()

    def __init__(self, task_func, task_kwargs, cancel_token=None) -> None:
        super().__init__()
        self.task_func    = task_func
        self.task_kwargs  = task_kwargs
        self.cancel_token = cancel_token

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            result = self.task_func(**self.task_kwargs)
            if self.cancel_token is not None and self.cancel_token.is_cancelled():
                self.cancelled.emit()
            else:
                self.result.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())


class PersistentWorkerExecutor(QtCore.QObject):
    """
    Runs each task on its own dedicated QThread that lives for the duration of
    the task function.  Unlike PoolExecutor, the thread is never shared with
    other tasks and is not returned to any pool — it exists solely for this one
    long-lived function call (e.g. a background scanner loop).

    The task function is expected to loop internally and exit only when
    cancel_token.is_cancelled() becomes True.  Call handle.cancel() to stop it.
    """

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._threads: dict[str, QtCore.QThread] = {}
        self._workers: dict[str, _PersistentWorker] = {}

    def submit(self, request: TaskRequest, kwargs: dict, cancel_token=None) -> _PersistentWorker:
        if request.task_id in self._threads:
            raise ValueError(f"Persistent task already running: {request.task_id}")

        thread = QtCore.QThread(self)
        thread.setObjectName(f"persistent-{request.task_type}")

        worker = _PersistentWorker(request.task_func, kwargs, cancel_token=cancel_token)
        worker.moveToThread(thread)

        tid = request.task_id
        thread.started.connect(worker.run)

        # Thread quits when the task function returns (any outcome).
        worker.result.connect(   lambda _r: thread.quit())
        worker.error.connect(    lambda _e: thread.quit())
        worker.cancelled.connect(thread.quit)

        worker.result.connect(   worker.deleteLater)
        worker.error.connect(    worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        thread.finished.connect( thread.deleteLater)
        thread.finished.connect( lambda t=tid: self._cleanup(t))

        self._threads[tid] = thread
        self._workers[tid] = worker

        # Run at low OS priority so the scanner never starves the UI.
        thread.start(QtCore.QThread.Priority.LowPriority)
        return worker

    def stop(self, task_id: str) -> None:
        """Request the thread to stop and block until it exits (max 5 s)."""
        thread = self._threads.get(task_id)
        if thread is not None:
            thread.quit()
            thread.wait(5000)

    def stop_all(self, timeout_ms: int = 3000) -> None:
        """Wait for every persistent thread to exit.  Callers must cancel the
        tasks' tokens FIRST — the loops end on cancellation, not on quit().
        Prevents Qt6's hard abort 'QThread: Destroyed while thread is still
        running' at application teardown."""
        for tid, thread in list(self._threads.items()):
            try:
                thread.quit()
                if not thread.wait(timeout_ms):
                    log.warning("Persistent thread %s did not stop within "
                                "%d ms", tid, timeout_ms)
            except RuntimeError:
                pass   # C++ object already gone

    def _cleanup(self, task_id: str) -> None:
        self._workers.pop(task_id, None)
        self._threads.pop(task_id, None)
