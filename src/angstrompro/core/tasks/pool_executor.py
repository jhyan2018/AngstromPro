# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 16:36:05 2026

@author: jiahaoYan
"""
import traceback

from angstrompro.utils.qt_compat import QtCore, Signal

from .task_request import TaskRequest

_PRIORITY_MAP = {"high": 10, "normal": 0, "low": -10}


class _RunSignals(QtCore.QObject):
    started   = Signal()
    progress  = Signal(int, int)  # current, total
    result    = Signal(object)
    error     = Signal(str)
    cancelled = Signal()


class _Runnable(QtCore.QRunnable):
    def __init__(self, task_func, task_kwargs, cancel_token=None) -> None:
        super().__init__()
        self.task_func    = task_func
        self.task_kwargs  = task_kwargs
        self.cancel_token = cancel_token
        self.signals      = _RunSignals()

    def run(self) -> None:
        self.signals.started.emit()
        try:
            result = self.task_func(**self.task_kwargs)
            if self.cancel_token is not None and self.cancel_token.is_cancelled():
                self.signals.cancelled.emit()
            else:
                self.signals.result.emit(result)
        except Exception:
            self.signals.error.emit(traceback.format_exc())


class PoolExecutor(QtCore.QObject):
    def __init__(self, max_thread_count: int = 4, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(max_thread_count)
        self._runnables: dict[str, _Runnable] = {}

    def submit(self, request: TaskRequest, kwargs: dict, cancel_token=None) -> _RunSignals:
        """Submit task with pre-built kwargs (cancel_token/progress_callback already injected)."""
        if request.task_id in self._runnables:
            raise ValueError(f"Task already running: {request.task_id}")

        runnable = _Runnable(request.task_func, kwargs, cancel_token=cancel_token)
        tid = request.task_id
        runnable.signals.result.connect(   lambda r, t=tid: self._cleanup(t))
        runnable.signals.error.connect(    lambda e, t=tid: self._cleanup(t))
        runnable.signals.cancelled.connect(lambda    t=tid: self._cleanup(t))

        self._runnables[tid] = runnable
        self._pool.start(runnable, _PRIORITY_MAP.get(request.priority, 0))
        return runnable.signals

    def _cleanup(self, task_id: str) -> None:
        self._runnables.pop(task_id, None)
