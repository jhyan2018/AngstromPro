# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 16:35:50 2026

@author: jiahaoYan
"""
import traceback

from angstrompro.utils.qt_compat import QtCore, Signal, Slot

from .task_request import TaskRequest
from .pool_executor import _RunSignals


class _Worker(QtCore.QObject):
    started   = Signal()
    progress  = Signal(int, int)
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


class WorkerExecutor(QtCore.QObject):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._threads: dict[str, QtCore.QThread] = {}
        self._workers: dict[str, _Worker]        = {}

    def submit(self, request: TaskRequest, kwargs: dict, cancel_token=None) -> _Worker:
        """Submit task with pre-built kwargs. Returns the worker object (has same signals as _RunSignals)."""
        if request.task_id in self._threads:
            raise ValueError(f"Task already running: {request.task_id}")

        thread = QtCore.QThread(self)
        worker = _Worker(request.task_func, kwargs, cancel_token=cancel_token)
        worker.moveToThread(thread)

        tid = request.task_id
        thread.started.connect(worker.run)
        worker.result.connect(   lambda r: thread.quit())
        worker.error.connect(    lambda e: thread.quit())
        worker.cancelled.connect(lambda:   thread.quit())
        worker.result.connect(   worker.deleteLater)
        worker.error.connect(    worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=tid: self._cleanup(t))

        self._threads[tid] = thread
        self._workers[tid] = worker
        thread.start()
        return worker

    def _cleanup(self, task_id: str) -> None:
        self._workers.pop(task_id, None)
        self._threads.pop(task_id, None)
