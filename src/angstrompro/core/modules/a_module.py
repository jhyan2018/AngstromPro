# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:46:45 2026

@author: jiahaoYan

AModule — pure Python base for all AngstromPro modules.

Holds the workspace and module identity. No Qt dependency — usable in
headless/batch contexts and independently testable.

"""

from __future__ import annotations

from angstrompro.core.workspaces.workspace import Workspace


class AModule:
    module_id:      str      = ""
    display_name:   str      = ""
    description:    str      = ""
    accepted_types: set[str] = set()   # empty = accept all types

    def __init__(
        self,
        module_id:    str | None = None,
        display_name: str | None = None,
        workspace:    Workspace  | None = None,
    ) -> None:
        if module_id:
            self.module_id = module_id
        if display_name:
            self.display_name = display_name
        # workspace is injected by whoever creates the module
        # (AGuiModule or a headless factory) so it is always properly
        # registered with WorkspaceManager before being handed here
        self.workspace: Workspace = workspace or Workspace(
            owner_id = self.module_id,
            label    = self.display_name or self.module_id,
        )
