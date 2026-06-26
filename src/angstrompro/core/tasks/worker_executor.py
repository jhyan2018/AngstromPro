import traceback

from angstrompro.utils.qt_compat import QtCore, Signal, Slot

from .task_handle import TaskHandle
from .task_request import TaskRequest


class _WorkerObject(QtCore.QObject):
    started = Signal()
    result  = Signal(object)
    error   = Signal(str)

    def __init__(self, task_func, task_kwargs, metadata=None) -> None:
        super().__init__()
        self.task_func = task_func
        self.task_kwargs = task_kwargs or {}
        self.metadata = metadata or {}
    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            result = self.task_func(**self.task_kwargs)
            self.result.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())


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

        handle = TaskHandle(task_id=request.task_id, parent=self)

        thread.started.connect(worker.run)

        tid = request.task_id
        worker.started.connect(lambda    t=tid: handle.started.emit(t))
        worker.result.connect( lambda r, t=tid: handle.result.emit(t, r))
        worker.error.connect(  lambda e, t=tid: handle.error.emit(t, e))

        worker.result.connect(lambda r: thread.quit())
        worker.error.connect( lambda e: thread.quit())
        worker.result.connect(worker.deleteLater)
        worker.error.connect( worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=tid: self._cleanup(t))

        self._threads[request.task_id] = thread
        self._workers[request.task_id] = worker
        thread.start()
        return handle

    def _cleanup(self, task_id: str) -> None:
        self._workers.pop(task_id, None)
        self._threads.pop(task_id, None)
