# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 16:37:10 2026

@author: jiahaoYan
"""
import logging

from angstrompro.utils.qt_compat import QtCore

from .task_dispatcher import TaskDispatcher
from .task_handle import TaskHandle
from .task_request import TaskRequest

log = logging.getLogger(__name__)


class TaskManager(QtCore.QObject):
    def __init__(
        self,
        compute_threads: int = 0,   # 0 = cpu_count
        io_threads:      int = 16,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._dispatcher = TaskDispatcher(compute_threads, io_threads, parent=self)
        self._handles:  dict[str, TaskHandle]    = {}
        self._requests: dict[str, TaskRequest]   = {}
        self._timers:   dict[str, QtCore.QTimer] = {}
        self._groups:   dict[str, set[str]]      = {}  # group_id → task_ids

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit(self, request: TaskRequest) -> TaskHandle:
        handle = TaskHandle(task_id=request.task_id, parent=self)
        self._handles[request.task_id]  = handle
        self._requests[request.task_id] = request
        if request.group_id:
            self._groups.setdefault(request.group_id, set()).add(request.task_id)
        self._run_attempt(request, handle, retries_left=request.retries, first=True)
        log.debug("Submitted: %s  type=%s  source=%s  backend=%s",
                  request.task_id[:8], request.task_type, request.source_id, request.backend)
        return handle

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _run_attempt(
        self,
        request: TaskRequest,
        handle: TaskHandle,
        retries_left: int,
        first: bool,
    ) -> None:
        progress_cb = None
        if request.has_progress:
            tid = request.task_id
            progress_cb = lambda cur, tot, t=tid: handle.progress.emit(t, cur, tot)

        signals, cancel_token = self._dispatcher.submit(request, progress_cb)

        if cancel_token is not None:
            handle._cancel_func = cancel_token.cancel

        tid = request.task_id

        if first:
            signals.started.connect(lambda t=tid: handle.started.emit(t))

        signals.result.connect(   lambda r, t=tid:                   self._on_result(t, r))
        signals.error.connect(    lambda e, t=tid, rl=retries_left:  self._on_error(t, e, rl))
        signals.cancelled.connect(lambda    t=tid:                   self._on_cancelled(t))

        if request.timeout_s is not None:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda t=tid: self._on_timeout(t))
            self._timers[tid] = timer
            signals.started.connect(
                lambda t=tid: self._timers[t].start(int(request.timeout_s * 1000))
                if t in self._timers else None
            )

    def _on_result(self, task_id: str, result_obj) -> None:
        handle = self._handles.get(task_id)
        if handle:
            handle.result.emit(task_id, result_obj)
        self._finish(task_id)

    def _on_error(self, task_id: str, error_text: str, retries_left: int) -> None:
        request = self._requests.get(task_id)
        handle  = self._handles.get(task_id)
        if request and handle and retries_left > 0:
            log.debug("Retrying %s (%d left)  type=%s", task_id[:8], retries_left, request.task_type)
            self._run_attempt(request, handle, retries_left - 1, first=False)
        else:
            if handle:
                handle.error.emit(task_id, error_text)
            self._finish(task_id)

    def _on_cancelled(self, task_id: str) -> None:
        handle = self._handles.get(task_id)
        if handle:
            handle.cancelled.emit(task_id)
        self._finish(task_id)

    def _on_timeout(self, task_id: str) -> None:
        handle = self._handles.get(task_id)
        if handle:
            handle.error.emit(task_id, f"Task timed out ({task_id[:8]})")
        self._finish(task_id)

    def _finish(self, task_id: str) -> None:
        self._handles.pop(task_id, None)
        self._requests.pop(task_id, None)
        timer = self._timers.pop(task_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        for members in self._groups.values():
            members.discard(task_id)
        log.debug("Task done: %s", task_id[:8])

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def is_running(self, task_id: str) -> bool:
        return task_id in self._handles

    def active_task_ids(self) -> list[str]:
        return list(self._handles.keys())

    def active_count(self) -> int:
        return len(self._handles)

    def group_task_ids(self, group_id: str) -> list[str]:
        return list(self._groups.get(group_id, set()))

    def cancel_group(self, group_id: str) -> None:
        for tid in list(self._groups.get(group_id, set())):
            handle = self._handles.get(tid)
            if handle:
                handle.cancel()
        log.debug("cancel_group: %s", group_id)
