from typing import Callable

from angstrompro.utils.qt_compat import QtCore, Signal


class TaskHandle(QtCore.QObject):
    started   = Signal(str)           # task_id
    progress  = Signal(str, int, int) # task_id, current, total
    result    = Signal(str, object)   # task_id, result_obj
    error     = Signal(str, str)      # task_id, traceback_text
    cancelled = Signal(str)           # task_id

    def __init__(
        self,
        task_id: str,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.task_id = task_id
        self._cancel_func: Callable[[], None] | None = None

    def cancel(self) -> None:
        if self._cancel_func is not None:
            self._cancel_func()
