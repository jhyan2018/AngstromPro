# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:37:07 2026

@author: jiahaoYan
"""
            
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from angstrompro.core.data.base import WorkspaceData


@dataclass
class WorkspaceItem:
    """A single data item held inside a Workspace.

    name        — stable internal name; used in ProcRecord and proc_history replay
    alias       — optional short display name shown in GUI (e.g. "ref", "before anneal")
                  falls back to name when not set
    payload     — the runtime data object (UdsDataStru, DataScene, or any future type)
    source_path — file this item was loaded from, if any
    item_id     — stable UUID, survives rename
    """
    name:        str
    payload:     WorkspaceData
    item_id:     str         = field(default_factory=lambda: f"item_{uuid.uuid4().hex[:12]}")
    source_path: Path | None = None
    alias:       str | None  = None

    @property
    def display_name(self) -> str:
        return self.alias if self.alias else self.name

    @property
    def type_id(self) -> str:
        return self.payload.type_id

