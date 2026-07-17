# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 16:37:53 2026

@author: jiahaoYan
"""

from threading import Lock


class CancelToken:
    def __init__(self) -> None:
        self._lock = Lock()
        self._cancelled = False

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled
