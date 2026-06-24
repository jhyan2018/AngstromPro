# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:21:47 2026

@author: jiahaoYan
"""

# src/angstrompro/processing/process_registry.py

from __future__ import annotations

from typing import Any


class ProcessRegistry:
    """
    Registry for processing algorithms.

    Later each algorithm can be represented by a ProcessSpec.
    """

    def __init__(self) -> None:
        self._processes: dict[str, Any] = {}

    def register(self, name: str, process_spec: Any, *, overwrite: bool = False) -> None:
        if name in self._processes and not overwrite:
            raise KeyError(f"Process already registered: {name}")

        self._processes[name] = process_spec

    def get(self, name: str) -> Any:
        return self._processes[name]

    def names(self) -> list[str]:
        return list(self._processes.keys())

    def clear(self) -> None:
        self._processes.clear()