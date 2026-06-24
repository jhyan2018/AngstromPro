from typing import Any, Callable


class TaskRequest:
    def __init__(
        self,
        task_id: str,
        task_func: Callable,
        kwargs: dict[str, Any] | None = None,
        backend: str = "auto",   # "auto" | "pool" | "worker"
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.task_id = task_id
        self.task_func = task_func
        self.kwargs: dict[str, Any] = kwargs or {}
        self.backend = backend
        self.metadata: dict[str, Any] = metadata or {}
