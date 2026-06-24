from typing import Callable

from angstrompro.utils.qt_compat import QtCore, Signal


class TaskHandle(QtCore.QObject):
    progress = Signal(str, int, str)   # task_id, percent, message
    result   = Signal(str, object)     # task_id, result_obj
    error    = Signal(str, str)        # task_id, traceback_text
    finished = Signal(str)            # task_id

    def __init__(
        self,
        task_id: str,
        cancel_func: Callable[[], None],
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.task_id = task_id
        self._cancel_func = cancel_func

    def cancel(self) -> None:
        self._cancel_func()
