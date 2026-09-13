# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:37:07 2026

@author: jiahaoYan
"""
            
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from angstrompro.core.data.base import WorkspaceData
from angstrompro.core.data.annotation_data import AnnotationData


@dataclass
class WorkspaceItem:
    """A single data item held inside a Workspace.

    payload     — the runtime data object; its payload.name is the item's identity
    alias       — optional display label shown in the GUI (e.g. "ref"); it
                  never changes item identity and is retained by workspace archives
    item_id     — stable UUID, survives rename
    annotations — dict mapping role name to annotation data (e.g. "bragg_peaks", "interest_region")
    """
    payload:     WorkspaceData
    item_id:     str         = field(default_factory=lambda: f"item_{uuid.uuid4().hex[:12]}")
    alias:       str         = ""
    annotations: dict[str, AnnotationData] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.payload.name

    @property
    def display_name(self) -> str:
        return self.alias if self.alias else self.payload.name

    @property
    def type_id(self) -> str:
        return self.payload.type_id

