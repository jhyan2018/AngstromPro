# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:20:17 2026

@author: jiahaoYan

AModuleManager — discovers and instantiates all registered AModule subclasses.

Registration
------------
    from angstrompro.core.modules.a_module_manager import register_module

    @register_module
    class Plot1U2(AModule):
        module_id    = "plot1u2"
        display_name = "Plot 1D/2D"
        ...

Usage
-----
    manager = AModuleManager()
    manager.load_builtin()

    for cls in manager.list_all():
        print(cls.module_id, cls.display_name)

    instance = manager.create("plot1u2", context, parent=window)
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type

from angstrompro.utils.qt_compat import QtCore, Signal
from .a_module import AModule
from .a_gui_module import AGuiModule

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext

log = logging.getLogger(__name__)

_PENDING: list[Type[AModule] | Type[AGuiModule]] = []


def register_module(cls):
    """Class decorator — registers an AModule or AGuiModule subclass."""
    if not cls.module_id:
        raise ValueError(f"{cls.__name__} must define a non-empty module_id")
    _PENDING.append(cls)
    return cls


class AModuleManager(QtCore.QObject):

    module_opened = Signal(str)   # module_id — emitted when an instance is created
    module_closed = Signal(str)   # module_id — emitted when an instance is destroyed

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._modules: dict[str, Type[AModule]] = {}

    def load_builtin(self) -> None:
        """Import all built-in module packages to trigger @register_module."""
        try:
            import angstrompro.gui.modules  # noqa: F401
        except ImportError:
            pass   # no built-in modules yet — fine during early development
        self._snapshot()
        log.debug("AModuleManager: %d built-in module(s) loaded", len(self._modules))

    def load_user_modules(self, directory: Path) -> None:
        """Dynamically import user .py files from a directory."""
        if not directory.exists():
            return
        before = set(self._modules.keys())
        for path in sorted(directory.glob("*.py")):
            if path.stem.startswith("_"):
                continue
            module_name = f"angstrompro_user_module.{path.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod
                spec.loader.exec_module(mod)
                log.info("Loaded user module file: %s", path.name)
            except Exception as exc:
                log.error("Failed to load user module %s: %s", path.name, exc)
        self._snapshot()
        new_count = len(self._modules) - len(before)
        if new_count:
            log.info("Registered %d user module(s) from %s", new_count, directory)

    def _snapshot(self) -> None:
        for cls in _PENDING:
            if cls.module_id not in self._modules:
                self._modules[cls.module_id] = cls

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, module_id: str) -> Type[AModule]:
        if module_id not in self._modules:
            raise KeyError(f"Unknown module: {module_id!r}")
        return self._modules[module_id]

    def has(self, module_id: str) -> bool:
        return module_id in self._modules

    def list_all(self) -> list[Type[AModule]]:
        return list(self._modules.values())

    # ------------------------------------------------------------------
    # Instantiate
    # ------------------------------------------------------------------

    def create(self, module_id: str, context: "AppContext",
               parent=None) -> AModule:
        """Instantiate a registered module class by module_id."""
        cls = self.get(module_id)
        instance = cls(context, parent=parent)
        self.module_opened.emit(module_id)
        return instance

    def close(self, module_id: str, instance: AModule) -> None:
        """Call when a registered module instance is closed/destroyed."""
        instance.deleteLater()
        self.module_closed.emit(module_id)