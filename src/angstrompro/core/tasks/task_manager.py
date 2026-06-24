# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:21:05 2026

@author: jiahaoYan
"""

# src/angstrompro/tasks/task_manager.py

from __future__ import annotations

from .pool_executor import ThreadPoolExecutor
from .worker_executor import WorkerThreadExecutor
from .task_dispatcher import TaskDispatcher
from .task_handle import TaskHandle
from .task_request import TaskRequest

class TaskManager:
    def __init__(self, max_pool_threads: int = 4):
        self._pool_executor   = ThreadPoolExecutor(max_pool_threads)
        self._worker_executor = WorkerThreadExecutor()
        self._dispatcher      = TaskDispatcher(self._pool_executor, self._worker_executor)
        self._active: dict[str, TaskHandle] = {}

    def submit(self, request: TaskRequest) -> TaskHandle:
        handle = self._dispatcher.submit(request)
        self._active[request.task_id] = handle
        handle.finished.connect(lambda tid: self._active.pop(tid, None))
        return handle

    def cancel_all(self) -> None:
        for handle in list(self._active.values()):
            handle.cancel()