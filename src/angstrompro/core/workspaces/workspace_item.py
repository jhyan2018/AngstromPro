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


def derived_process_alias(primary_item, output_name: str) -> str:
    """Build an output alias from a primary input's explicit alias.

    Only exact-name and delimiter-prefixed suffix relationships are accepted.
    This keeps aliases predictable and avoids labelling unrelated outputs as
    though they were simple derivatives of the input.
    """
    if primary_item is None or not getattr(primary_item, "alias", ""):
        return ""
    input_name = primary_item.name
    if output_name == input_name:
        return primary_item.alias
    if not input_name or not output_name.startswith(input_name):
        return ""
    suffix = output_name[len(input_name):]
    if not suffix.startswith(("_", "-", " ", ".", "[", "(")):
        return ""
    return primary_item.alias + suffix


@dataclass
class WorkspaceItem:
    """A single data item held inside a Workspace.

    payload     — the runtime data object; its payload.name is the item's identity
    alias       — optional display label shown in the GUI (e.g. "ref"); it
                  never changes item identity and is retained by workspace archives
    item_id     — stable UUID, survives rename
    annotations — dict mapping role name to annotation data (e.g. "bragg_peaks", "interest_region")
    metadata    — generic structured records independent of the payload type
    """
    payload:     WorkspaceData
    item_id:     str         = field(default_factory=lambda: f"item_{uuid.uuid4().hex[:12]}")
    alias:       str         = ""
    annotations: dict[str, AnnotationData] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.payload.name

    @property
    def display_name(self) -> str:
        return self.alias if self.alias else self.payload.name

    @property
    def type_id(self) -> str:
        return self.payload.type_id

