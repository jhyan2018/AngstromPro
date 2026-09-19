# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 2026

@author: jiahaoYan

ModuleMixin shared identity and resource base for all AngstromPro modules.

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

from angstrompro.core.processes.process_runner import ProcessRunner

if TYPE_CHECKING:
    from angstrompro.app.app_context import AppContext
    from angstrompro.core.workspaces.workspace import Workspace
    from angstrompro.core.workspaces.workspace_item import WorkspaceItem


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
        self.private_workspace: "Workspace" = context.workspace_manager.create_workspace(
            owner_id = self.instance_id,
            label    = self.display_name or self.module_id,
        )
        self.shared_workspace: "Workspace | None" = None
        # ``workspace`` remains the write/output target for source
        # compatibility.  It points at the private workspace until a shared
        # workspace is attached, then at that shared workspace.
        self.workspace: "Workspace" = self.private_workspace
        self._workspace_attachment_slot = self._on_workspace_attachment_changed
        context.workspace_manager.module_attachment_changed.connect(
            self._workspace_attachment_slot)
        self.process_runner: ProcessRunner = ProcessRunner(context.tasks, context.processes)
        # Staged inputs for the next process run. Each module maintains this list
        # by its own strategy. Processes consume the first N items in schema order.
        # AGuiModule overrides process_inputs as a property; set the backing attr
        # directly here so the property setter doesn't fire before _ws_list exists.
        if not hasattr(self, '_process_inputs'):
            self._process_inputs: list["WorkspaceItem"] = []
        # Future resources (e.g. plugin bus, settings scope) go here.

    def _on_workspace_attachment_changed(
            self, instance_id: str, workspace_id: str) -> None:
        if instance_id != self.instance_id:
            return
        if workspace_id:
            shared = self._context.workspace_manager.get_workspace(workspace_id)
            if not shared.is_shared:
                raise ValueError("Attached workspace must be shared")
            self.shared_workspace = shared
            self.workspace = shared
        else:
            self.shared_workspace = None
            self.workspace = self.private_workspace

        callback = getattr(self, "on_workspace_attachment_changed", None)
        if callable(callback):
            callback()

    def accessible_workspaces(self) -> list["Workspace"]:
        """Private workspace plus the optional attached shared workspace."""
        workspaces = [self.private_workspace]
        if self.shared_workspace is not None:
            workspaces.append(self.shared_workspace)
        return workspaces

    def accessible_workspace_items(self) -> list["WorkspaceItem"]:
        return [
            item
            for workspace in self.accessible_workspaces()
            for item in workspace.list_items()
        ]

    def workspace_containing_item(
            self, item: "WorkspaceItem") -> "Workspace | None":
        for workspace in self.accessible_workspaces():
            existing = workspace.find_item_by_id(item.item_id)
            if existing is item:
                return workspace
        return self._context.workspace_manager.workspace_for_item(item)

    def notify_workspace_item_changed(self, item: "WorkspaceItem") -> None:
        workspace = self.workspace_containing_item(item)
        if workspace is not None:
            workspace.notify_changed(item.name)

    def find_accessible_item(
            self, name: str, *,
            preferred_item: "WorkspaceItem | None" = None,
    ) -> "WorkspaceItem | None":
        """Find an item by name, preferring the supplied item's workspace."""
        preferred_workspace = (
            self.workspace_containing_item(preferred_item)
            if preferred_item is not None else None
        )
        ordered = []
        if preferred_workspace is not None:
            ordered.append(preferred_workspace)
        if self.workspace not in ordered:
            ordered.append(self.workspace)
        for workspace in self.accessible_workspaces():
            if workspace not in ordered:
                ordered.append(workspace)
        for workspace in ordered:
            item = workspace.find_item(name)
            if item is not None:
                return item
        return None

    def _dispose_module_workspaces(self) -> None:
        """Detach the module and unregister its private workspace."""
        manager = self._context.workspace_manager
        manager.detach_module(self.instance_id)
        try:
            manager.module_attachment_changed.disconnect(
                self._workspace_attachment_slot)
        except (TypeError, RuntimeError):
            pass
        manager.remove_workspace(self.private_workspace.workspace_id)
