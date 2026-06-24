from angstrompro.utils.qt_compat import QtCore

from .task_handle import TaskHandle
from .task_request import TaskRequest
from .pool_executor import ThreadPoolExecutor
from .worker_executor import WorkerThreadExecutor


class TaskDispatcher(QtCore.QObject):
    def __init__(
        self,
        pool_executor: ThreadPoolExecutor,
        worker_executor: WorkerThreadExecutor,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.pool_executor = pool_executor
        self.worker_executor = worker_executor

    def submit(self, request: TaskRequest) -> TaskHandle:
        if request.backend == "pool":
            return self.pool_executor.submit(request)
        elif request.backend == "worker":
            return self.worker_executor.submit(request)
        elif request.backend == "auto":
            return self._submit_auto(request)
        else:
            raise ValueError(f"Unknown backend: {request.backend!r}")

    def _submit_auto(self, request: TaskRequest) -> TaskHandle:
        if request.metadata.get("needs_dedicated_thread", False):
            return self.worker_executor.submit(request)
        return self.pool_executor.submit(request)
