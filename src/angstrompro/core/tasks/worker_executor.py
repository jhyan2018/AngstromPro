import traceback

from angstrompro.utils.qt_compat import QtCore, Signal, Slot

from .cancel_token import CancelToken
from .task_context import TaskContext
from .task_handle import TaskHandle
from .task_request import TaskRequest


class _WorkerObject(QtCore.QObject):
    progress = Signal(int, str)
    result   = Signal(object)
    error    = Signal(str)
    finished = Signal()

    def __init__(self, task_func, task_kwargs, metadata=None) -> None:
        super().__init__()
        self.task_func = task_func
        self.task_kwargs = task_kwargs or {}
        self.metadata = metadata or {}
        self.cancel_token = CancelToken()

    @Slot()
    def run(self) -> None:
        try:
            ctx = TaskContext(
                task_id="",
                progress_callback=lambda p, m: self.progress.emit(p, m),
                cancel_token=self.cancel_token,
                metadata=self.metadata,
            )
            result = self.task_func(ctx, **self.task_kwargs)
            self.result.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self.cancel_token.cancel()


class WorkerThreadExecutor(QtCore.QObject):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._threads: dict[str, QtCore.QThread] = {}
        self._workers: dict[str, _WorkerObject] = {}

    def submit(self, request: TaskRequest) -> TaskHandle:
        if request.task_id in self._threads:
            raise ValueError(f"Task already exists: {request.task_id}")

        thread = QtCore.QThread(self)
        worker = _WorkerObject(
            task_func=request.task_func,
            task_kwargs=request.kwargs,
            metadata=request.metadata,
        )
        worker.moveToThread(thread)

        handle = TaskHandle(task_id=request.task_id, cancel_func=worker.cancel, parent=self)

        thread.started.connect(worker.run)

        tid = request.task_id
        worker.progress.connect(lambda p, m, t=tid: handle.progress.emit(t, p, m))
        worker.result.connect(  lambda r,    t=tid: handle.result.emit(t, r))
        worker.error.connect(   lambda e,    t=tid: handle.error.emit(t, e))
        worker.finished.connect(lambda       t=tid: handle.finished.emit(t))

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=tid: self._cleanup(t))

        self._threads[request.task_id] = thread
        self._workers[request.task_id] = worker
        thread.start()
        return handle

    def _cleanup(self, task_id: str) -> None:
        self._workers.pop(task_id, None)
        self._threads.pop(task_id, None)
