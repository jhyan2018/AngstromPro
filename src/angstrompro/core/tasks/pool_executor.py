import traceback

from angstrompro.utils.qt_compat import QtCore, Signal

from .cancel_token import CancelToken
from .task_context import TaskContext
from .task_handle import TaskHandle
from .task_request import TaskRequest


class _PoolRunnableSignals(QtCore.QObject):
    progress = Signal(int, str)
    result   = Signal(object)
    error    = Signal(str)
    finished = Signal()


class _PoolRunnable(QtCore.QRunnable):
    def __init__(self, task_func, task_kwargs, metadata=None) -> None:
        super().__init__()
        self.task_func = task_func
        self.task_kwargs = task_kwargs or {}
        self.metadata = metadata or {}
        self.signals = _PoolRunnableSignals()
        self.cancel_token = CancelToken()

    def cancel(self) -> None:
        self.cancel_token.cancel()

    def run(self) -> None:
        try:
            ctx = TaskContext(
                task_id="",
                progress_callback=lambda p, m: self.signals.progress.emit(p, m),
                cancel_token=self.cancel_token,
                metadata=self.metadata,
            )
            result = self.task_func(ctx, **self.task_kwargs)
            self.signals.result.emit(result)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()


class ThreadPoolExecutor(QtCore.QObject):
    def __init__(self, max_thread_count: int = 4, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QtCore.QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(max_thread_count)
        self._tasks: dict[str, _PoolRunnable] = {}

    def submit(self, request: TaskRequest) -> TaskHandle:
        if request.task_id in self._tasks:
            raise ValueError(f"Task already exists: {request.task_id}")

        runnable = _PoolRunnable(
            task_func=request.task_func,
            task_kwargs=request.kwargs,
            metadata=request.metadata,
        )
        handle = TaskHandle(task_id=request.task_id, cancel_func=runnable.cancel, parent=self)

        tid = request.task_id
        runnable.signals.progress.connect(lambda p, m, t=tid: handle.progress.emit(t, p, m))
        runnable.signals.result.connect(  lambda r,    t=tid: handle.result.emit(t, r))
        runnable.signals.error.connect(   lambda e,    t=tid: handle.error.emit(t, e))
        runnable.signals.finished.connect(lambda       t=tid: handle.finished.emit(t))
        runnable.signals.finished.connect(lambda       t=tid: self._cleanup(t))

        self._tasks[request.task_id] = runnable
        self._pool.start(runnable)
        return handle

    def _cleanup(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)
