"""
ModuleMixin — shared identity and resource base for all AngstromPro modules.

Mixed into both AModule (headless) and AGuiModule (Qt window). Any new
per-module resource (e.g. settings scope, plugin bus) should be added here
so both GUI and non-GUI modules gain it automatically.

Usage
-----
    class AHeadlessModule(ModuleMixin): ...
    class AGuiModule(ModuleMixin, QtWidgets.QMainWindow): ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext
    from angstrompro.core.workspaces.workspace import Workspace


class ModuleMixin:
    """Pure-Python mixin — no Qt, safe for multiple inheritance with QObject subclasses."""

    # class-level type identifier — shared by all instances of a module type
    module_id:      str      = ""
    display_name:   str      = ""
    description:    str      = ""
    category:       str      = ""      # e.g. "imaging", "analysis" — empty = uncategorized
    accepted_types: set[str] = set()   # empty = accept all types

    _instance_counters: dict[str, int] = {}   # module_id → running count

    def _init_module(self, context: "AppContext") -> None:
        """Initialise all module-level resources. Call once from __init__."""
        self._context = context
        # per-type counter → human-friendly unique instance ID
        n = ModuleMixin._instance_counters.get(self.module_id, 0) + 1
        ModuleMixin._instance_counters[self.module_id] = n
        self.instance_number: int = n
        self.instance_id: str = f"{self.module_id}_{n}"
        self.workspace: "Workspace" = context.workspace_manager.create_workspace(
            owner_id = self.instance_id,
            label    = self.display_name or self.module_id,
        )
        # Future resources (e.g. plugin bus, settings scope) go here.
