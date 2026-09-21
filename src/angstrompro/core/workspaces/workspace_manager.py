# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:43:19 2026

@author: jiahaoYan

WorkspaceManager — global registry for all Workspace instances.

Each module creates a private Workspace via create_workspace().  The manager
also owns any number of application-level shared workspaces and records the
single optional shared-workspace attachment for each module instance.

Signals
-------
    workspace_created(workspace_id)
    workspace_removed(workspace_id)
    workspace_renamed(workspace_id, new_label)
    module_attachment_changed(instance_id, shared_workspace_id_or_empty)
    item_transferred(src_id, dst_id, item_name)
"""

from __future__ import annotations

import logging
import uuid
from copy import deepcopy

from angstrompro.utils.qt_compat import QtCore, Signal

from .workspace import Workspace
from .workspace_item import WorkspaceItem

log = logging.getLogger(__name__)


class WorkspaceManager(QtCore.QObject):
    workspace_created   = Signal(str)             # workspace_id
    workspace_removed   = Signal(str)             # workspace_id
    workspace_renamed   = Signal(str, str)        # workspace_id, new_label
    module_attachment_changed = Signal(str, str)  # instance_id, shared workspace id or ""
    item_added          = Signal(str, str)         # workspace_id, item_name
    item_removed        = Signal(str, str)         # workspace_id, item_name
    item_renamed        = Signal(str, str, str)    # workspace_id, old_name, new_name
    item_changed        = Signal(str, str)         # workspace_id, item_name
    item_transferred    = Signal(str, str, str)    # src_id, dst_id, item_name

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._workspaces: dict[str, Workspace] = {}
        self._module_attachments: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Workspace lifecycle
    # ------------------------------------------------------------------

    def create_workspace(
        self,
        owner_id: str,
        label:    str | None = None,
    ) -> Workspace:
        existing = self.find_by_owner(owner_id)
        if existing is not None:
            raise ValueError(f"Module {owner_id!r} already has a private workspace")
        ws = Workspace(owner_id=owner_id, label=label, parent=self)
        self._register_workspace(ws)
        return ws

    def create_shared_workspace(self, label: str) -> Workspace:
        """Create an application-owned shared workspace."""
        clean_label = label.strip()
        if not clean_label:
            raise ValueError("Shared workspace name cannot be empty")
        if any(ws.label == clean_label for ws in self.list_shared_workspaces()):
            raise ValueError(f"A shared workspace named {clean_label!r} already exists")
        ws = Workspace(
            owner_id=None,
            label=clean_label,
            workspace_id=f"shared_{uuid.uuid4().hex[:12]}",
            is_shared=True,
            parent=self,
        )
        self._register_workspace(ws)
        return ws

    def _register_workspace(self, ws: Workspace) -> None:
        wid = ws.workspace_id

        if wid in self._workspaces:
            raise ValueError(f"Workspace id {wid!r} is already registered")

        ws.item_added.connect(  lambda name:     self.item_added.emit(wid, name))
        ws.item_removed.connect(lambda name:     self.item_removed.emit(wid, name))
        ws.item_renamed.connect(lambda old, new: self.item_renamed.emit(wid, old, new))
        ws.item_changed.connect(lambda name:     self.item_changed.emit(wid, name))

        self._workspaces[wid] = ws
        log.debug("Workspace created: %s (owner=%s, shared=%s)",
                  wid, ws.owner_id, ws.is_shared)
        self.workspace_created.emit(wid)

    def remove_workspace(self, workspace_id: str) -> None:
        ws = self._workspaces.pop(workspace_id, None)
        if ws:
            if ws.is_shared:
                for instance_id in list(self.attached_module_ids(workspace_id)):
                    self.detach_module(instance_id)
            log.debug("Workspace removed: %s", workspace_id)
            self.workspace_removed.emit(workspace_id)

    def rename_shared_workspace(self, workspace_id: str, label: str) -> None:
        ws = self.get_workspace(workspace_id)
        if not ws.is_shared:
            raise ValueError("Only shared workspaces can be renamed here")
        clean_label = label.strip()
        if not clean_label:
            raise ValueError("Shared workspace name cannot be empty")
        if any(other.workspace_id != workspace_id and other.label == clean_label
               for other in self.list_shared_workspaces()):
            raise ValueError(f"A shared workspace named {clean_label!r} already exists")
        if ws.label == clean_label:
            return
        ws.label = clean_label
        self.workspace_renamed.emit(workspace_id, clean_label)

    def remove_shared_workspace(self, workspace_id: str) -> None:
        ws = self.get_workspace(workspace_id)
        if not ws.is_shared:
            raise ValueError("Only shared workspaces can be removed here")
        self.remove_workspace(workspace_id)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_workspace(self, workspace_id: str) -> Workspace:
        if workspace_id not in self._workspaces:
            raise KeyError(f"No workspace with id {workspace_id!r}")
        return self._workspaces[workspace_id]

    def find_by_owner(self, owner_id: str) -> Workspace | None:
        for ws in self._workspaces.values():
            if ws.owner_id == owner_id:
                return ws
        return None

    @property
    def workspaces(self) -> dict[str, Workspace]:
        return self._workspaces

    def list_workspaces(self) -> list[Workspace]:
        return list(self._workspaces.values())

    def list_shared_workspaces(self) -> list[Workspace]:
        return [ws for ws in self._workspaces.values() if ws.is_shared]

    def count(self) -> int:
        return len(self._workspaces)

    # ------------------------------------------------------------------
    # Module attachments
    # ------------------------------------------------------------------

    def attach_module(self, instance_id: str, workspace_id: str) -> None:
        """Attach a module to exactly one shared workspace."""
        ws = self.get_workspace(workspace_id)
        if not ws.is_shared:
            raise ValueError("Modules can only attach to shared workspaces")
        if self._module_attachments.get(instance_id) == workspace_id:
            return
        self._module_attachments[instance_id] = workspace_id
        self.module_attachment_changed.emit(instance_id, workspace_id)

    def detach_module(self, instance_id: str) -> None:
        if self._module_attachments.pop(instance_id, None) is not None:
            self.module_attachment_changed.emit(instance_id, "")

    def shared_workspace_for_module(self, instance_id: str) -> Workspace | None:
        workspace_id = self._module_attachments.get(instance_id)
        return self._workspaces.get(workspace_id) if workspace_id else None

    def attached_module_ids(self, workspace_id: str) -> list[str]:
        return [
            instance_id
            for instance_id, attached_id in self._module_attachments.items()
            if attached_id == workspace_id
        ]

    def workspace_for_item(self, item: WorkspaceItem) -> Workspace | None:
        """Return the registered workspace that owns *item*."""
        for ws in self._workspaces.values():
            existing = ws.find_item_by_id(item.item_id)
            if existing is item:
                return ws
        return None

    # ------------------------------------------------------------------
    # Cross-workspace operations
    # ------------------------------------------------------------------

    def transfer_item(
        self,
        src_workspace_id: str,
        dst_workspace_id: str,
        item_name:        str,
        new_name:         str | None = None,
    ) -> WorkspaceItem:
        """Copy an item from one workspace to another. Original is kept."""
        src  = self.get_workspace(src_workspace_id)
        dst  = self.get_workspace(dst_workspace_id)
        item = src.get_item(item_name)
        payload = deepcopy(item.payload)
        if new_name:
            payload.name = new_name
        new_item = dst.add_item(
            payload=payload,
            alias=item.alias,
            annotations=deepcopy(item.annotations),
        )
        log.debug("Transferred %r: %s → %s", item.name,
                  src_workspace_id, dst_workspace_id)
        self.item_transferred.emit(src_workspace_id, dst_workspace_id, new_item.name)
        return new_item
