# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 16:20:17 2026

@author: jiahaoYan

AModuleManager — discovers and instantiates all registered AModule subclasses.

Registration
------------
    from angstrompro.core.modules.a_module_manager import register_module

    @register_module
    class Plot1U2(AHeadlessModule):
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
from .a_headless_module import AHeadlessModule
from .a_gui_module import AGuiModule
from .module_mixin import ModuleMixin

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext

log = logging.getLogger(__name__)

_PENDING: dict[str, Type[ModuleMixin]] = {}


def register_module(cls):
    """Class decorator — registers an AHeadlessModule or AGuiModule subclass."""
    if not cls.module_id:
        raise ValueError(f"{cls.__name__} must define a non-empty module_id")
    _PENDING[cls.module_id] = cls
    return cls


class AModuleManager(QtCore.QObject):

    module_added   = Signal(str)   # module_id — emitted when an instance is created
    module_removed = Signal(str)   # module_id — emitted when an instance is removed

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._modules:         dict[str, Type[ModuleMixin]] = {}
        self._instances:       dict[str, list[ModuleMixin]] = {}  # module_id → live instances
        self._default_targets: dict[str, list[str]]         = {}  # src_instance_id → [target_instance_ids]

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
        self._modules.update(_PENDING)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, module_id: str) -> Type[ModuleMixin]:
        if module_id not in self._modules:
            raise KeyError(f"Unknown module: {module_id!r}")
        return self._modules[module_id]

    def has(self, module_id: str) -> bool:
        return module_id in self._modules

    def list_all(self) -> list[Type[ModuleMixin]]:
        return list(self._modules.values())

    # ------------------------------------------------------------------
    # Instance tracking
    # ------------------------------------------------------------------

    def list_instances(self, module_id: str | None = None) -> list[ModuleMixin]:
        """Return all live instances, or only those of a given module_id."""
        if module_id is not None:
            return list(self._instances.get(module_id, []))
        return [inst for group in self._instances.values() for inst in group]

    def instance_count(self, module_id: str | None = None) -> int:
        return len(self.list_instances(module_id))

    # ------------------------------------------------------------------
    # Default send targets
    # ------------------------------------------------------------------

    def set_default_targets(self, src_instance_id: str,
                            target_instance_ids: list[str]) -> None:
        self._default_targets[src_instance_id] = list(target_instance_ids)

    def get_default_targets(self, src_instance_id: str) -> list[ModuleMixin]:
        """Return live default targets, silently dropping stale entries."""
        live = {inst.instance_id: inst for inst in self.list_instances()}
        return [
            live[tid]
            for tid in self._default_targets.get(src_instance_id, [])
            if tid in live
        ]

    def get_default_target_ids(self, src_instance_id: str) -> list[str]:
        return list(self._default_targets.get(src_instance_id, []))

    # ------------------------------------------------------------------
    # Instantiate
    # ------------------------------------------------------------------

    def create(self, module_id: str, context: "AppContext",
               parent=None) -> ModuleMixin:
        """Instantiate a registered module class by module_id."""
        self._snapshot()   # flush any @register_module calls that happened after load_builtin
        cls = self.get(module_id)
        instance = cls(context, parent=parent)
        self._instances.setdefault(module_id, []).append(instance)
        self.module_added.emit(module_id)
        log.debug("Module added: %s (instance_id=%s)", module_id, instance.instance_id)
        return instance

    def remove(self, instance: ModuleMixin) -> None:
        """Untrack and destroy a live module instance."""
        module_id = instance.module_id
        instances = self._instances.get(module_id, [])
        if instance in instances:
            instances.remove(instance)
        instance.deleteLater()
        self.module_removed.emit(module_id)
        log.debug("Module removed: %s (instance_id=%s)", module_id, instance.instance_id)