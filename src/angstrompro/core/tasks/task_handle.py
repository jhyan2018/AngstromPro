from angstrompro.utils.qt_compat import QtCore, Signal


class TaskHandle(QtCore.QObject):
    started = Signal(str)          # task_id
    result  = Signal(str, object)  # task_id, result_obj
    error   = Signal(str, str)     # task_id, traceback_text

    def __init__(
        self,
        task_id: str,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.task_id = task_id
