# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 16:35:28 2026

@author: jiahaoYan
"""
from typing import Any

from .cancel_token import CancelToken


class TaskContext:
    def __init__(
        self,
        task_id: str,
        cancel_token: CancelToken,
        metadata: dict | None = None,
    ) -> None:
        self.task_id = task_id
        self._cancel_token = cancel_token
        self.metadata: dict[str, Any] = metadata or {}

    def is_cancelled(self) -> bool:
        return self._cancel_token.is_cancelled()
