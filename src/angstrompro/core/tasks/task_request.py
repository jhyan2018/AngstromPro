import uuid
from typing import Any, Callable


class TaskRequest:
    def __init__(
        self,
        task_func:    Callable,
        source_id:    str,
        task_type:    str,
        kwargs:       dict[str, Any] | None = None,
        backend:      str  = "compute",  # "compute" | "io" | "worker" | "async"
        cancellable:  bool = False,
        has_progress: bool = False,
        priority:     str  = "normal",   # "high" | "normal" | "low"
        timeout_s:    float | None = None,
        retries:      int  = 0,
        group_id:     str  = "",
        metadata:     dict[str, Any] | None = None,
    ) -> None:
        self.task_id      = str(uuid.uuid4())
        self.task_func    = task_func
        self.source_id    = source_id
        self.task_type    = task_type
        self.kwargs       = kwargs or {}
        self.backend      = backend
        self.cancellable  = cancellable
        self.has_progress = has_progress
        self.priority     = priority
        self.timeout_s    = timeout_s
        self.retries      = retries
        self.group_id     = group_id
        self.metadata     = metadata or {}
