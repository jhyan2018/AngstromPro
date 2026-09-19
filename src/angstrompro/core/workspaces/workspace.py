# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:40:57 2026

@author: jiahaoYan
"""

from __future__ import annotations

from angstrompro.utils.qt_compat import QtCore, Signal
from angstrompro.core.data.annotation_data import AnnotationData
from angstrompro.core.data.base import WorkspaceData
from .workspace_item import WorkspaceItem


class Workspace(QtCore.QObject):
    """Named item container.

    Private workspaces belong to one module instance.  Shared workspaces have
    no owner and are managed at application level by :class:`WorkspaceManager`.
    """

    item_added   = Signal(str)         # item_name
    item_removed = Signal(str)         # item_name
    item_renamed = Signal(str, str)    # old_name, new_name
    item_changed = Signal(str)         # item_name — emitted when item data/annotations mutate

    def __init__(
        self,
        owner_id: str | None,
        label:    str | None = None,
        parent:   QtCore.QObject | None = None,
        *,
        workspace_id: str | None = None,
        is_shared: bool = False,
    ) -> None:
        super().__init__(parent)
        self.owner_id     = owner_id
        self.is_shared    = bool(is_shared)
        if self.is_shared and owner_id is not None:
            raise ValueError("A shared workspace cannot have a module owner")
        if workspace_id is None:
            if owner_id is None:
                raise ValueError("workspace_id is required when owner_id is None")
            workspace_id = f"ws_{owner_id}"
        self.workspace_id = workspace_id
        self.label        = label or owner_id or workspace_id
        self._items:      dict[str, WorkspaceItem] = {}
        self._item_order: list[str]                = []

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_item(
        self,
        payload:     WorkspaceData,
        *,
        alias:       str = "",
        annotations: dict[str, AnnotationData] | None = None,
        item_id:     str | None = None,
    ) -> WorkspaceItem:
        # Deduplicate by modifying payload.name directly
        base = payload.name or "item"
        if base in self._items:
            i = 2
            while f"{base}_{i}" in self._items:
                i += 1
            payload.name = f"{base}_{i}"
        name = payload.name
        item = WorkspaceItem(
            payload=payload,
            alias=alias,
            annotations=dict(annotations or {}),
        )
        if item_id and all(existing.item_id != item_id
                           for existing in self._items.values()):
            item.item_id = item_id
        self._item_order.append(name)
        self._items[name] = item
        self.item_added.emit(name)
        return item

    def remove_item(self, name: str) -> None:
        if name in self._items:
            del self._items[name]
            self._item_order.remove(name)
            self.item_removed.emit(name)

    def rename_item(self, old_name: str, new_name: str) -> None:
        if old_name not in self._items:
            raise KeyError(f"No item named {old_name!r}")
        if new_name in self._items:
            raise ValueError(f"Name {new_name!r} is already taken")
        item = self._items.pop(old_name)
        item.payload.name = new_name
        self._items[new_name] = item
        idx = self._item_order.index(old_name)
        self._item_order[idx] = new_name
        self.item_renamed.emit(old_name, new_name)

    def reorder(self, new_order: list[str]) -> None:
        if set(new_order) != set(self._items):
            raise ValueError("new_order must contain exactly the same names")
        self._item_order = list(new_order)

    def clear(self) -> None:
        for name in list(self._item_order):
            self.remove_item(name)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_item(self, name: str) -> WorkspaceItem:
        return self._items[name]

    def get_item_by_id(self, item_id: str) -> WorkspaceItem:
        item = self.find_item_by_id(item_id)
        if item is None:
            raise KeyError(f"No item with id {item_id!r}")
        return item

    def find_item(self, name: str) -> "WorkspaceItem | None":
        return self._items.get(name)

    def find_item_by_id(self, item_id: str) -> "WorkspaceItem | None":
        return next(
            (item for item in self._items.values() if item.item_id == item_id),
            None,
        )

    def get_payload(self, name: str) -> WorkspaceData:
        return self._items[name].payload

    def has_item(self, name: str) -> bool:
        return name in self._items

    def has_item_id(self, item_id: str) -> bool:
        return self.find_item_by_id(item_id) is not None

    def list_names(self) -> list[str]:
        return list(self._item_order)

    def list_items(self) -> list[WorkspaceItem]:
        return [self._items[n] for n in self._item_order]

    def count(self) -> int:
        return len(self._items)

    def by_type(self, type_id: str) -> list[WorkspaceItem]:
        return [i for i in self._items.values() if i.type_id == type_id]

    def notify_changed(self, name: str) -> None:
        """Emit item_changed signal for the given item name (e.g. after annotation mutation)."""
        if name in self._items:
            self.item_changed.emit(name)

