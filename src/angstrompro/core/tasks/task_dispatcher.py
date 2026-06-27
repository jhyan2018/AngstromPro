import os

from angstrompro.utils.qt_compat import QtCore

from .cancel_token import CancelToken
from .task_request import TaskRequest
from .pool_executor import PoolExecutor
from .worker_executor import WorkerExecutor


class TaskDispatcher(QtCore.QObject):
    """Routes TaskRequests to the appropriate executor and injects cancel_token / progress_callback."""

    def __init__(
        self,
        compute_threads: int = 0,   # 0 = cpu_count
        io_threads:      int = 16,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        n_cpu = compute_threads or max(1, os.cpu_count() or 4)
        self._compute = PoolExecutor(n_cpu,     parent=self)
        self._io      = PoolExecutor(io_threads, parent=self)
        self._worker  = WorkerExecutor(parent=self)

    def submit(self, request: TaskRequest, progress_cb=None):
        """
        Build kwargs, inject cancel_token / progress_callback, route to executor.
        Returns (signals, cancel_token | None).
        signals has: started(), progress(int,int), result(object), error(str).
        """
        cancel_token = None
        kwargs = dict(request.kwargs)

        if request.cancellable:
            cancel_token = CancelToken()
            kwargs["cancel_token"] = cancel_token

        if request.has_progress and progress_cb is not None:
            kwargs["progress_callback"] = progress_cb

        if request.backend in ("compute", "auto"):
            signals = self._compute.submit(request, kwargs, cancel_token=cancel_token)
        elif request.backend == "io":
            signals = self._io.submit(request, kwargs, cancel_token=cancel_token)
        elif request.backend == "worker":
            signals = self._worker.submit(request, kwargs, cancel_token=cancel_token)
        elif request.backend == "async":
            signals = self._io.submit(request, kwargs, cancel_token=cancel_token)
        else:
            raise ValueError(f"Unknown backend: {request.backend!r}")

        return signals, cancel_token
