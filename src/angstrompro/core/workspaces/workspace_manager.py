# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:43:19 2026

@author: jiahaoYan

WorkspaceManager — global registry for all Workspace instances.

Each module creates its own Workspace via create_workspace().
WorkspaceManager can transfer items between workspaces.

Signals
-------
    workspace_created(workspace_id)
    workspace_removed(workspace_id)
    item_transferred(src_id, dst_id, item_name)
"""

from __future__ import annotations

import logging

from angstrompro.utils.qt_compat import QtCore, Signal

from .workspace import Workspace
from .workspace_item import WorkspaceItem

log = logging.getLogger(__name__)


class WorkspaceManager(QtCore.QObject):
    workspace_created   = Signal(str)             # workspace_id
    workspace_removed   = Signal(str)             # workspace_id
    item_added          = Signal(str, str)         # workspace_id, item_name
    item_removed        = Signal(str, str)         # workspace_id, item_name
    item_renamed        = Signal(str, str, str)    # workspace_id, old_name, new_name
    item_transferred    = Signal(str, str, str)    # src_id, dst_id, item_name

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._workspaces: dict[str, Workspace] = {}

    # ------------------------------------------------------------------
    # Workspace lifecycle
    # ------------------------------------------------------------------

    def create_workspace(
        self,
        owner_id: str,
        label:    str | None = None,
    ) -> Workspace:
        ws = Workspace(owner_id=owner_id, label=label)
        wid = ws.workspace_id

        # Wrap mutating methods to emit manager-level signals
        _orig_add    = ws.add_item
        _orig_remove = ws.remove_item
        _orig_rename = ws.rename_item

        def _add(name, payload, source_path=None):
            item = _orig_add(name, payload, source_path)
            self.item_added.emit(wid, name)
            return item

        def _remove(name):
            _orig_remove(name)
            self.item_removed.emit(wid, name)

        def _rename(old_name, new_name):
            _orig_rename(old_name, new_name)
            self.item_renamed.emit(wid, old_name, new_name)

        ws.add_item    = _add
        ws.remove_item = _remove
        ws.rename_item = _rename

        self._workspaces[wid] = ws
        log.debug("Workspace created: %s (owner=%s)", wid, owner_id)
        self.workspace_created.emit(wid)
        return ws

    def remove_workspace(self, workspace_id: str) -> None:
        ws = self._workspaces.pop(workspace_id, None)
        if ws:
            log.debug("Workspace removed: %s", workspace_id)
            self.workspace_removed.emit(workspace_id)

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

    def count(self) -> int:
        return len(self._workspaces)

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
        name = new_name or dst.suggest_name(item_name)
        new_item = dst.add_item(
            name=name,
            payload=item.payload,
            source_path=item.source_path,
        )
        log.debug("Transferred %r: %s → %s", item_name,
                  src_workspace_id, dst_workspace_id)
        self.item_transferred.emit(src_workspace_id, dst_workspace_id, name)
        return new_item

        