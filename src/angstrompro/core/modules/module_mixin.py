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

from contextlib import contextmanager
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
        self._active_workspace: "Workspace" = self.private_workspace
        self._process_output_workspace: "Workspace | None" = None
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
            previous_shared = self.shared_workspace
            self.shared_workspace = shared
            # Preserve the existing first-attachment default. Once the user
            # chooses private, replacing a shared attachment does not undo it.
            if previous_shared is None or self.active_workspace is previous_shared:
                self._active_workspace = shared
        else:
            self.shared_workspace = None
            self._active_workspace = self.private_workspace

        callback = getattr(self, "on_workspace_attachment_changed", None)
        if callable(callback):
            callback()

    @property
    def active_workspace(self) -> "Workspace":
        """Destination selected by this module, independently of attachment."""
        return self._active_workspace

    @property
    def workspace(self) -> "Workspace":
        """Output destination; pinned during a submitted process's callback."""
        if self._process_output_workspace is not None:
            return self._process_output_workspace
        return self.active_workspace

    @workspace.setter
    def workspace(self, workspace: "Workspace") -> None:
        # Retain compatibility with modules assigning their output destination.
        if workspace not in self.accessible_workspaces():
            raise ValueError("The destination must be this module's private or attached workspace")
        self.set_active_workspace(workspace.workspace_id)

    def set_active_workspace(self, workspace_id: str) -> None:
        workspace = next((ws for ws in self.accessible_workspaces()
                          if ws.workspace_id == workspace_id), None)
        if workspace is None:
            raise ValueError("The destination must be this module's private or attached workspace")
        if workspace is self.active_workspace:
            return
        self._active_workspace = workspace
        callback = getattr(self, "on_active_workspace_changed", None)
        if callable(callback):
            callback()

    @contextmanager
    def _process_output_scope(self, workspace: "Workspace"):
        """Keep legacy callbacks using self.workspace on their captured target."""
        previous = self._process_output_workspace
        self._process_output_workspace = workspace
        try:
            yield
        finally:
            self._process_output_workspace = previous

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
