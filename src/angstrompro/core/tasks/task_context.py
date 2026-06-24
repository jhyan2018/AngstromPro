from typing import Any, Callable

from .cancel_token import CancelToken


class TaskContext:
    def __init__(
        self,
        task_id: str,
        progress_callback: Callable[[int, str], None],
        cancel_token: CancelToken,
        metadata: dict | None = None,
    ) -> None:
        self.task_id = task_id
        self._progress_callback = progress_callback
        self._cancel_token = cancel_token
        self.metadata: dict[str, Any] = metadata or {}

    def set_progress(self, percent: float, message: str = "") -> None:
        self._progress_callback(int(percent), str(message))

    def is_cancelled(self) -> bool:
        return self._cancel_token.is_cancelled()
